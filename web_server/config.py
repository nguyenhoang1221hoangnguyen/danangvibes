from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    storage_path: Path
    server_db_path: Path
    bundle_inbox_path: Path
    admin_token: str
    max_selfie_size_mb: int
    face_top_k: int
    face_similarity_threshold: float


def load_settings() -> Settings:
    import logging
    storage_path = Path(os.getenv("DANANGVIBES_STORAGE_PATH", "./storage/events"))
    log_level = os.getenv("DANANGVIBES_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO), format="%(name)s %(levelname)s %(message)s")
    logging.getLogger("web_server").setLevel(getattr(logging, log_level, logging.INFO))
    logging.getLogger("processing_cli").setLevel(getattr(logging, log_level, logging.INFO))
    return Settings(
        host=os.getenv("DANANGVIBES_HOST", "127.0.0.1"),
        port=int(os.getenv("DANANGVIBES_PORT", "8000")),
        storage_path=storage_path,
        server_db_path=Path(os.getenv("DANANGVIBES_SERVER_DB_PATH", str(storage_path / "server.db"))),
        bundle_inbox_path=Path(os.getenv("DANANGVIBES_BUNDLE_INBOX_PATH", "./inbox/bundles")),
        admin_token=os.getenv("DANANGVIBES_ADMIN_TOKEN", ""),
        max_selfie_size_mb=int(os.getenv("DANANGVIBES_MAX_SELFIE_SIZE_MB", "10")),
        face_top_k=int(os.getenv("DANANGVIBES_FACE_TOP_K", "50")),
        face_similarity_threshold=float(os.getenv("DANANGVIBES_FACE_SIMILARITY_THRESHOLD", "0.6")),
    )


settings = load_settings()
