from __future__ import annotations

import argparse
from pathlib import Path

from web_server.config import settings
from web_server.server_database import connect_server_database
from web_server.services.importer import set_published, switch_version


def _versions(event_slug: str, server_db_path: Path) -> None:
    connection = connect_server_database(server_db_path)
    try:
        event = connection.execute("SELECT * FROM server_events WHERE slug = ?", (event_slug,)).fetchone()
        rows = connection.execute(
            "SELECT version, imported_at, bundle_path FROM event_versions WHERE event_slug = ? ORDER BY imported_at",
            (event_slug,),
        ).fetchall()
    finally:
        connection.close()
    if not event:
        raise FileNotFoundError(f"Event not found: {event_slug}")
    print(f"Event: {event_slug}")
    print(f"Active: {event['active_version']}")
    print(f"Published: {'yes' if event['is_published'] else 'no'}")
    for row in rows:
        marker = " (active)" if row["version"] == event["active_version"] else ""
        print(f"{row['version']} - {row['imported_at']}{marker}")


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    switch_parser = subparsers.add_parser("switch-version", help="Switch active event version")
    switch_parser.add_argument("--event-slug", required=True)
    switch_parser.add_argument("--version", required=True)
    switch_parser.add_argument("--storage-path", default=settings.storage_path, type=Path)
    switch_parser.add_argument("--server-db-path", default=settings.server_db_path, type=Path)
    switch_parser.set_defaults(handler=lambda args: switch_version(args.storage_path, args.server_db_path, args.event_slug, args.version))

    rollback_parser = subparsers.add_parser("rollback", help="Rollback active event version")
    rollback_parser.add_argument("--event-slug", required=True)
    rollback_parser.add_argument("--version", required=True)
    rollback_parser.add_argument("--storage-path", default=settings.storage_path, type=Path)
    rollback_parser.add_argument("--server-db-path", default=settings.server_db_path, type=Path)
    rollback_parser.set_defaults(handler=lambda args: switch_version(args.storage_path, args.server_db_path, args.event_slug, args.version))

    publish_parser = subparsers.add_parser("publish", help="Publish event")
    publish_parser.add_argument("--event-slug", required=True)
    publish_parser.add_argument("--server-db-path", default=settings.server_db_path, type=Path)
    publish_parser.set_defaults(handler=lambda args: set_published(args.server_db_path, args.event_slug, True))

    unpublish_parser = subparsers.add_parser("unpublish", help="Unpublish event")
    unpublish_parser.add_argument("--event-slug", required=True)
    unpublish_parser.add_argument("--server-db-path", default=settings.server_db_path, type=Path)
    unpublish_parser.set_defaults(handler=lambda args: set_published(args.server_db_path, args.event_slug, False))

    list_parser = subparsers.add_parser("list-versions", help="List event versions")
    list_parser.add_argument("--event-slug", required=True)
    list_parser.add_argument("--server-db-path", default=settings.server_db_path, type=Path)
    list_parser.set_defaults(handler=lambda args: _versions(args.event_slug, args.server_db_path))
