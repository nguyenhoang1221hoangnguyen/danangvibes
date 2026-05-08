from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_ROOT / "static"
TEMPLATES_DIR = PACKAGE_ROOT / "templates"
QR_UPLOAD_DIR = STATIC_DIR / "uploads" / "qr"
