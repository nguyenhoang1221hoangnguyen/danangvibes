#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PROCESSING_HOST="${PROCESSING_HOST:-127.0.0.1}"
PROCESSING_PORT="${PROCESSING_PORT:-8010}"
WEB_HOST="${WEB_HOST:-127.0.0.1}"
WEB_PORT="${WEB_PORT:-8000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-${DANANGVIBES_ADMIN_TOKEN:-}}"
STORAGE_PATH="${STORAGE_PATH:-$PROJECT_ROOT/storage/events}"
BUNDLE_INBOX_PATH="${BUNDLE_INBOX_PATH:-$PROJECT_ROOT/inbox/bundles}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/dist/events}"

cleanup() {
  if [ -n "${PROCESSING_PID:-}" ]; then
    kill "$PROCESSING_PID" 2>/dev/null || true
  fi
  if [ -n "${WEB_PID:-}" ]; then
    kill "$WEB_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null
}
trap cleanup EXIT INT TERM

usage() {
  cat <<'USAGE'
Usage:
  ADMIN_TOKEN=dev-secret scripts/start-all.sh

Starts both the Processing Web App and the Web Server side by side.
Press Ctrl+C to stop both.

Required env:
  ADMIN_TOKEN=dev-secret       # admin auth token for the web server

Optional env:
  PROCESSING_HOST=127.0.0.1    # processing app bind host
  PROCESSING_PORT=8010          # processing app bind port
  WEB_HOST=127.0.0.1           # web server bind host
  WEB_PORT=8000                 # web server bind port
  STORAGE_PATH=storage/events  # web server storage dir
  BUNDLE_INBOX_PATH=inbox/bundles
  OUTPUT_DIR=dist/events       # processing output dir
USAGE
}

if [ -z "$ADMIN_TOKEN" ]; then
  usage
  exit 2
fi

mkdir -p "$STORAGE_PATH" "$BUNDLE_INBOX_PATH" "$OUTPUT_DIR"

# Start Processing Web App in background
HOST="$PROCESSING_HOST" \
PORT="$PROCESSING_PORT" \
OUTPUT_DIR="$OUTPUT_DIR" \
  "$PROJECT_ROOT/scripts/start-processing-app.sh" &
PROCESSING_PID=$!

# Give processing app a moment to start its venv setup
sleep 1

# Start Web Server in background
HOST="$WEB_HOST" \
PORT="$WEB_PORT" \
STORAGE_PATH="$STORAGE_PATH" \
BUNDLE_INBOX_PATH="$BUNDLE_INBOX_PATH" \
ADMIN_TOKEN="$ADMIN_TOKEN" \
  "$PROJECT_ROOT/scripts/start-web-app.sh" &
WEB_PID=$!

cat <<EOF

==========================================
  DaNang Vibes - All Services Running
==========================================

  Processing UI:  http://$PROCESSING_HOST:$PROCESSING_PORT
  Web UI:         http://$WEB_HOST:$WEB_PORT
  Admin UI:       http://$WEB_HOST:$WEB_PORT/admin/
  Output dir:     $OUTPUT_DIR
  Inbox:          $BUNDLE_INBOX_PATH

  Press Ctrl+C to stop all services.
==========================================

EOF

wait
