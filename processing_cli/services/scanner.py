from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

ALLOWED_EXTENSIONS = {".jpg", ".jpeg"}


class PhotoScanner:
    def scan(self, source_path: Path) -> Iterator[Path]:
        if not source_path.is_dir():
            raise NotADirectoryError(f"Source must be a directory: {source_path}")
        for file_path in sorted(source_path.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS and not file_path.name.startswith("."):
                yield file_path
