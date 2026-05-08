from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from shared.bundle import validate_bundle
from shared.checksum import compute_checksum
from web_server.server_database import connect_server_database


def next_version(storage_path: Path, event_slug: str) -> str:
    releases = storage_path / event_slug / "releases"
    if not releases.exists():
        return "v1"
    numbers = []
    for child in releases.iterdir():
        if child.is_dir() and child.name.startswith("v") and child.name[1:].isdigit():
            numbers.append(int(child.name[1:]))
    return f"v{max(numbers, default=0) + 1}"


def import_bundle(bundle: Path, storage_path: Path, server_db_path: Path, version: str | None = None) -> str:
    manifest = validate_bundle(bundle)
    event_slug = manifest.event.slug
    selected_version = version or next_version(storage_path, event_slug)
    event_dir = storage_path / event_slug
    releases_dir = event_dir / "releases"
    target_dir = releases_dir / selected_version
    tmp_dir = releases_dir / f".{selected_version}.tmp"
    if target_dir.exists():
        raise FileExistsError(f"Version already exists: {target_dir}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    releases_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle, tmp_dir)
    tmp_dir.rename(target_dir)

    active_link = event_dir / "active"
    created_active_link = False
    if not active_link.exists():
        active_link.symlink_to(Path("releases") / selected_version)
        created_active_link = True

    connection = connect_server_database(server_db_path)
    try:
        now = datetime.utcnow().isoformat()
        existing = connection.execute(
            "SELECT active_version FROM server_events WHERE slug = ?", (event_slug,)
        ).fetchone()
        active_version = selected_version if existing is None or created_active_link else existing["active_version"]
        connection.execute(
            """
            INSERT INTO server_events (slug, name, active_version, is_published, storage_path, created_at, updated_at)
            VALUES (?, ?, ?, 0, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET name = excluded.name, updated_at = excluded.updated_at
            """,
            (event_slug, manifest.event.name, active_version, str(event_dir), now, now),
        )
        connection.execute(
            """
            INSERT INTO event_versions (event_slug, version, bundle_path, manifest_checksum)
            VALUES (?, ?, ?, ?)
            """,
            (event_slug, selected_version, str(target_dir), compute_checksum(target_dir / "manifest.json")),
        )
        connection.commit()
    finally:
        connection.close()
    return selected_version


def switch_version(storage_path: Path, server_db_path: Path, event_slug: str, version: str) -> None:
    event_dir = storage_path / event_slug
    target = event_dir / "releases" / version
    if not target.is_dir():
        raise FileNotFoundError(f"Version not found: {target}")
    active_link = event_dir / "active"
    if active_link.exists() or active_link.is_symlink():
        active_link.unlink()
    active_link.symlink_to(Path("releases") / version)
    connection = connect_server_database(server_db_path)
    try:
        connection.execute(
            "UPDATE server_events SET active_version = ?, updated_at = ? WHERE slug = ?",
            (version, datetime.utcnow().isoformat(), event_slug),
        )
        connection.commit()
    finally:
        connection.close()


def set_published(server_db_path: Path, event_slug: str, published: bool) -> None:
    connection = connect_server_database(server_db_path)
    try:
        connection.execute(
            "UPDATE server_events SET is_published = ?, updated_at = ? WHERE slug = ?",
            (1 if published else 0, datetime.utcnow().isoformat(), event_slug),
        )
        connection.commit()
    finally:
        connection.close()
