#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

BUNDLE_PATH="${BUNDLE_PATH:-}"
STORAGE_PATH="${STORAGE_PATH:-$PROJECT_ROOT/storage/events}"
SERVER_DB_PATH="${SERVER_DB_PATH:-$STORAGE_PATH/server.db}"
EVENT_SLUG="${EVENT_SLUG:-}"
VERSION="${VERSION:-}"
PUBLISH="${PUBLISH:-1}"

usage() {
  cat <<'USAGE'
Usage:
  BUNDLE_PATH=dist/events/test-event EVENT_SLUG=test-event scripts/import-and-publish-bundle.sh

Optional env:
  STORAGE_PATH=storage/events
  SERVER_DB_PATH=storage/events/server.db
  VERSION=v2
  PUBLISH=0           # import only, do not publish
USAGE
}

if [ -z "$BUNDLE_PATH" ] || [ -z "$EVENT_SLUG" ]; then
  usage
  exit 2
fi

mkdir -p "$STORAGE_PATH"

import_args=(
  -m web_server import
  --bundle "$BUNDLE_PATH"
  --storage-path "$STORAGE_PATH"
  --server-db-path "$SERVER_DB_PATH"
)

if [ -n "$VERSION" ]; then
  import_args+=(--version "$VERSION")
fi

"$PYTHON_BIN" "${import_args[@]}"

if [ "$PUBLISH" = "1" ]; then
  "$PYTHON_BIN" -m web_server publish --event-slug "$EVENT_SLUG" --server-db-path "$SERVER_DB_PATH"
fi

"$PYTHON_BIN" -m web_server list-versions --event-slug "$EVENT_SLUG" --server-db-path "$SERVER_DB_PATH"
