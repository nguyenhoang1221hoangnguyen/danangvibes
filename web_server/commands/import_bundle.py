from __future__ import annotations

import argparse
from pathlib import Path

from web_server.config import settings
from web_server.services.importer import import_bundle


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("import", help="Import bundle into server storage")
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--storage-path", default=settings.storage_path, type=Path)
    parser.add_argument("--server-db-path", default=settings.server_db_path, type=Path)
    parser.add_argument("--version")
    parser.set_defaults(
        handler=lambda args: print(
            f"Imported {args.bundle} as {import_bundle(args.bundle, args.storage_path, args.server_db_path, args.version)}"
        )
    )
