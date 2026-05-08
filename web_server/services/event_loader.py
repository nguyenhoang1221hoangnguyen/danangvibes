from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock

from shared.bundle import EMPTY_FAISS_SENTINEL, load_manifest
from shared.database import connect_database
from shared.models import BundleManifest
from web_server.server_database import connect_server_database


class EventBundle:
    def __init__(self, slug: str, bundle_path: Path) -> None:
        self.slug = slug
        self.bundle_path = bundle_path
        self.manifest: BundleManifest = load_manifest(bundle_path)
        self.originals_mapping: dict[str, object] | None = None

        if self.manifest.files.originals_mapping:
            mapping_path = bundle_path / self.manifest.files.originals_mapping
            if mapping_path.exists():
                self.originals_mapping = json.loads(mapping_path.read_text(encoding="utf-8"))

    def get_connection(self, *, readonly: bool = True) -> sqlite3.Connection:
        return connect_database(self.bundle_path / self.manifest.files.database, readonly=readonly)

    def get_original_path(self, photo_id: int) -> Path | None:
        if not self.originals_mapping:
            return None
        mode = self.originals_mapping.get("mode", "mapping")
        mappings = self.originals_mapping.get("mappings", {})
        if not isinstance(mappings, dict):
            return None

        if mode == "embedded":
            filename = mappings.get(str(photo_id))
            if not filename:
                return None
            base_path = (self.bundle_path / "originals").resolve()
            relative = Path(str(filename))
            if relative.is_absolute() or ".." in relative.parts:
                return None
            candidate = (base_path / relative).resolve()
            return candidate if candidate.exists() and (base_path == candidate or base_path in candidate.parents) else None

        # mapping mode: resolve from external base_path
        base_value = self.originals_mapping.get("base_path")
        if not isinstance(base_value, str):
            return None
        relative_value = mappings.get(str(photo_id))
        if not relative_value:
            return None
        relative = Path(str(relative_value))
        if relative.is_absolute() or ".." in relative.parts:
            return None
        base_path = Path(base_value).resolve()
        candidate = (base_path / relative).resolve()
        return candidate if base_path == candidate or base_path in candidate.parents else None

    def load_faiss_index(self):
        faiss_path = self.bundle_path / self.manifest.files.faiss_index
        if faiss_path.stat().st_size == len(EMPTY_FAISS_SENTINEL) and faiss_path.read_bytes() == EMPTY_FAISS_SENTINEL:
            return None
        try:
            import faiss
        except ImportError as exc:
            raise RuntimeError("Install faiss-cpu to enable face search") from exc
        return faiss.read_index(str(faiss_path))


class EventLoader:
    def __init__(self, storage_path: Path, server_db_path: Path) -> None:
        self.storage_path = storage_path
        self.server_db_path = server_db_path
        self.bundles: dict[str, EventBundle] = {}
        self._lock = RLock()
        self.storage_path.mkdir(parents=True, exist_ok=True)
        connect_server_database(server_db_path).close()

    def load_published_events(self) -> None:
        connection = connect_server_database(self.server_db_path)
        try:
            rows = connection.execute("SELECT slug FROM server_events WHERE is_published = 1").fetchall()
        finally:
            connection.close()
        for row in rows:
            self.reload_event(str(row["slug"]))

    def reload_event(self, slug: str) -> EventBundle:
        event_dir = self.storage_path / slug
        active_link = event_dir / "active"
        if not active_link.exists():
            raise FileNotFoundError(f"Active bundle not found for event: {slug}")
        bundle = EventBundle(slug, active_link.resolve())
        with self._lock:
            self.bundles[slug] = bundle
        return bundle

    def load_event(self, slug: str) -> EventBundle:
        with self._lock:
            cached = self.bundles.get(slug)
        return cached if cached else self.reload_event(slug)

    def get_event(self, slug: str) -> EventBundle | None:
        with self._lock:
            cached = self.bundles.get(slug)
        if cached:
            return cached
        connection = connect_server_database(self.server_db_path)
        try:
            row = connection.execute(
                "SELECT slug FROM server_events WHERE slug = ? AND is_published = 1", (slug,)
            ).fetchone()
        finally:
            connection.close()
        return self.load_event(slug) if row else None

    def unload_event(self, slug: str) -> None:
        with self._lock:
            self.bundles.pop(slug, None)