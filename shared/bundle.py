from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from shared.checksum import compute_checksum
from shared.database import connect_database
from shared.models import BundleManifest

REQUIRED_TABLES = {"events", "photos", "thumbnails", "ocr_candidates", "faces"}
EMPTY_FAISS_SENTINEL = b"danangvibes-empty-faiss\n"


def write_manifest(bundle_path: Path, manifest: BundleManifest) -> None:
    bundle_path.mkdir(parents=True, exist_ok=True)
    (bundle_path / "manifest.json").write_text(
        json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_manifest(bundle_path: Path) -> BundleManifest:
    manifest_path = bundle_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")
    return BundleManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))


def validate_database_schema(db_path: Path) -> None:
    if not db_path.exists():
        raise FileNotFoundError(f"Missing database: {db_path}")
    connection = connect_database(db_path, readonly=True)
    try:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        tables = {str(row["name"]) for row in rows}
        missing = REQUIRED_TABLES - tables
        if missing:
            raise ValueError(f"Database missing tables: {', '.join(sorted(missing))}")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise ValueError(f"Database integrity check failed: {db_path}")
    finally:
        connection.close()


def validate_bundle(bundle_path: Path, *, verify_checksums: bool = True) -> BundleManifest:
    manifest = load_manifest(bundle_path)
    db_path = bundle_path / manifest.files.database
    faiss_path = bundle_path / manifest.files.faiss_index
    thumbnails_dir = bundle_path / manifest.files.thumbnails_dir

    validate_database_schema(db_path)
    if not faiss_path.exists():
        raise FileNotFoundError(f"Missing FAISS index: {faiss_path}")
    if not thumbnails_dir.is_dir():
        raise FileNotFoundError(f"Missing thumbnails directory: {thumbnails_dir}")
    mapping = manifest.files.originals_mapping
    if not mapping or not (bundle_path / mapping).exists():
        raise FileNotFoundError("Missing originals_mapping.json")

    if verify_checksums:
        for relative_path, expected in manifest.checksums.items():
            file_path = bundle_path / relative_path
            if compute_checksum(file_path) != expected:
                raise ValueError(f"Checksum mismatch: {relative_path}")
    return manifest


def read_photo_count(db_path: Path) -> int:
    connection = connect_database(db_path, readonly=True)
    try:
        return int(connection.execute("SELECT COUNT(*) FROM photos").fetchone()[0])
    except sqlite3.DatabaseError as exc:
        raise ValueError(f"Invalid bundle database: {db_path}") from exc
    finally:
        connection.close()
