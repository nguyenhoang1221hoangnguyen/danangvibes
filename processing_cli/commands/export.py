from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from shared.bundle import validate_bundle


def run(bundle: Path, output: Path | None, compress: bool) -> None:
    validate_bundle(bundle)
    if compress:
        target = output or bundle.with_suffix(".zip")
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for file_path in bundle.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(bundle.parent))
        print(f"Bundle exported to {target}")
        return
    print(f"Bundle ready at {bundle}")
    print(f"Copy with: cp -R {bundle} /Volumes/ExternalSSD/bundles/")


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("export", help="Validate and optionally zip a bundle")
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compress", action="store_true")
    parser.set_defaults(handler=lambda args: run(args.bundle, args.output, args.compress))
