#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
STORAGE_PATH="${STORAGE_PATH:-$PROJECT_ROOT/storage/events}"
SERVER_DB_PATH="${SERVER_DB_PATH:-$STORAGE_PATH/server.db}"
BUNDLE_INBOX_PATH="${BUNDLE_INBOX_PATH:-$PROJECT_ROOT/inbox/bundles}"
ADMIN_TOKEN="${ADMIN_TOKEN:-${DANANGVIBES_ADMIN_TOKEN:-}}"

if [ -z "$ADMIN_TOKEN" ]; then
  cat <<'USAGE'
ADMIN_TOKEN is required.
Example:
  ADMIN_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" scripts/run-web-server.sh
USAGE
  exit 2
fi

mkdir -p "$STORAGE_PATH" "$BUNDLE_INBOX_PATH"

export DANANGVIBES_HOST="$HOST"
export DANANGVIBES_PORT="$PORT"
export DANANGVIBES_STORAGE_PATH="$STORAGE_PATH"
export DANANGVIBES_SERVER_DB_PATH="$SERVER_DB_PATH"
export DANANGVIBES_BUNDLE_INBOX_PATH="$BUNDLE_INBOX_PATH"
export DANANGVIBES_ADMIN_TOKEN="$ADMIN_TOKEN"

exec "$PYTHON_BIN" -m web_server run \
  --host "$HOST" \
  --port "$PORT" \
  --storage-path "$STORAGE_PATH"
