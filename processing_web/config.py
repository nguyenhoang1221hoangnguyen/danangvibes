from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from processing_cli.commands.process import DEFAULT_CONFIG_PATH


@dataclass(frozen=True)
class ProcessingSettings:
    host: str
    port: int
    output_root: Path
    config_path: Path


def load_settings() -> ProcessingSettings:
    return ProcessingSettings(
        host=os.getenv("DANANGVIBES_PROCESSING_HOST", "127.0.0.1"),
        port=int(os.getenv("DANANGVIBES_PROCESSING_PORT", "8010")),
        output_root=Path(os.getenv("DANANGVIBES_PROCESSING_OUTPUT_ROOT", "./dist/events")),
        config_path=Path(os.getenv("DANANGVIBES_PROCESSING_CONFIG_PATH", str(DEFAULT_CONFIG_PATH))),
    )


settings = load_settings()
