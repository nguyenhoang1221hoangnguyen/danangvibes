from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect_database(db_path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        uri = f"file:{db_path}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: Path) -> sqlite3.Connection:
    connection = connect_database(db_path)
    connection.executescript(SCHEMA_PATH.read_text())
    connection.commit()
    return connection
