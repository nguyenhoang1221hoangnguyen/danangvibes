from __future__ import annotations

import argparse
from pathlib import Path

from shared.bundle import validate_bundle


def run(bundle: Path) -> None:
    manifest = validate_bundle(bundle)
    print(f"Bundle valid: {manifest.event.slug}")


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("validate", help="Validate an event bundle")
    parser.add_argument("--bundle", required=True, type=Path)
    parser.set_defaults(handler=lambda args: run(args.bundle))
