from __future__ import annotations

import argparse

from web_server.commands import import_bundle, version
from web_server.config import settings


def _run_server(host: str, port: int, storage_path: str | None) -> None:
    import os

    if storage_path:
        from pathlib import Path

        os.environ["DANANGVIBES_STORAGE_PATH"] = storage_path
        os.environ.setdefault("DANANGVIBES_SERVER_DB_PATH", str(Path(storage_path) / "server.db"))
    import uvicorn

    uvicorn.run("web_server.main:app", host=host, port=port, reload=False)


def main() -> None:
    parser = argparse.ArgumentParser(prog="web_server", description="DaNang Vibes Web Server")
    subparsers = parser.add_subparsers(dest="command", required=True)
    import_bundle.register(subparsers)
    version.register(subparsers)

    run_parser = subparsers.add_parser("run", help="Run FastAPI server")
    run_parser.add_argument("--host", default=settings.host)
    run_parser.add_argument("--port", default=settings.port, type=int)
    run_parser.add_argument("--storage-path")
    run_parser.set_defaults(handler=lambda args: _run_server(args.host, args.port, args.storage_path))

    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
