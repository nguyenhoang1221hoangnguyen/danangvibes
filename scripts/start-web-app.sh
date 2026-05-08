#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
STORAGE_PATH="${STORAGE_PATH:-$PROJECT_ROOT/storage/events}"
SERVER_DB_PATH="${SERVER_DB_PATH:-$STORAGE_PATH/server.db}"
BUNDLE_INBOX_PATH="${BUNDLE_INBOX_PATH:-$PROJECT_ROOT/inbox/bundles}"
ADMIN_TOKEN="${ADMIN_TOKEN:-${DANANGVIBES_ADMIN_TOKEN:-}}"

usage() {
  cat <<'USAGE'
Usage:
  ADMIN_TOKEN=dev-secret scripts/start-web-app.sh

Optional env:
  HOST=127.0.0.1
  PORT=8000
  STORAGE_PATH=storage/events
  BUNDLE_INBOX_PATH=inbox/bundles
USAGE
}

if [ -z "$ADMIN_TOKEN" ]; then
  usage
  exit 2
fi

INSTALL_AI=0 "$PROJECT_ROOT/scripts/setup-local-env.sh"
mkdir -p "$STORAGE_PATH" "$BUNDLE_INBOX_PATH"

cat <<EOF

Web app is starting.
Web UI:    http://$HOST:$PORT
Admin UI:  http://$HOST:$PORT/admin/
Inbox:     $BUNDLE_INBOX_PATH

Copy bundle folders from USB/SSD into the inbox, then import them from Admin UI.
EOF

HOST="$HOST" \
PORT="$PORT" \
STORAGE_PATH="$STORAGE_PATH" \
SERVER_DB_PATH="$SERVER_DB_PATH" \
BUNDLE_INBOX_PATH="$BUNDLE_INBOX_PATH" \
ADMIN_TOKEN="$ADMIN_TOKEN" \
  "$PROJECT_ROOT/scripts/run-web-server.sh"
