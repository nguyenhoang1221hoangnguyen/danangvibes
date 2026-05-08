from __future__ import annotations

import argparse

from processing_cli.commands import batch_process, export, process, rebuild_embeddings, validate


def main() -> None:
    parser = argparse.ArgumentParser(prog="processing_cli", description="DaNang Vibes Processing CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    process.register(subparsers)
    batch_process.register(subparsers)
    validate.register(subparsers)
    export.register(subparsers)
    rebuild_embeddings.register(subparsers)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
