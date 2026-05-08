from __future__ import annotations

import argparse

import uvicorn

from processing_web.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="processing_web")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="Run Processing Web App")
    run_parser.add_argument("--host", default=settings.host)
    run_parser.add_argument("--port", default=settings.port, type=int)
    args = parser.parse_args()
    if args.command == "run":
        uvicorn.run("processing_web.main:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
