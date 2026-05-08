#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SOURCE_DIR="${SOURCE_DIR:-}"
EVENT_SLUG="${EVENT_SLUG:-}"
EVENT_NAME="${EVENT_NAME:-}"
EVENT_DATE="${EVENT_DATE:-}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/dist/events}"
STORAGE_PATH="${STORAGE_PATH:-$PROJECT_ROOT/storage/events}"
ADMIN_TOKEN="${ADMIN_TOKEN:-${DANANGVIBES_ADMIN_TOKEN:-}}"
SKIP_PROCESSING="${SKIP_PROCESSING:-0}"
SKIP_IMPORT="${SKIP_IMPORT:-0}"

usage() {
  cat <<'USAGE'
Usage:
  SOURCE_DIR=/path/to/photos \
  EVENT_SLUG=test-event \
  EVENT_NAME="Test Event" \
  EVENT_DATE=2026-05-07 \
  ADMIN_TOKEN=dev-secret \
  scripts/start-all-local.sh

Optional env:
  SKIP_PROCESSING=1   # reuse existing dist/events/$EVENT_SLUG
  SKIP_IMPORT=1       # assume event already imported/published
  STORAGE_PATH=storage/events
  OUTPUT_DIR=dist/events
USAGE
}

if [ -z "$EVENT_SLUG" ] || [ -z "$ADMIN_TOKEN" ]; then
  usage
  exit 2
fi

if [ "$SKIP_PROCESSING" != "1" ]; then
  if [ -z "$SOURCE_DIR" ] || [ -z "$EVENT_NAME" ] || [ -z "$EVENT_DATE" ]; then
    usage
    exit 2
  fi
  SOURCE_DIR="$SOURCE_DIR" EVENT_SLUG="$EVENT_SLUG" EVENT_NAME="$EVENT_NAME" EVENT_DATE="$EVENT_DATE" OUTPUT_DIR="$OUTPUT_DIR" \
    "$PROJECT_ROOT/scripts/run-processing-cli.sh"
fi

if [ "$SKIP_IMPORT" != "1" ]; then
  BUNDLE_PATH="$OUTPUT_DIR/$EVENT_SLUG" EVENT_SLUG="$EVENT_SLUG" STORAGE_PATH="$STORAGE_PATH" \
    "$PROJECT_ROOT/scripts/import-and-publish-bundle.sh"
fi

ADMIN_TOKEN="$ADMIN_TOKEN" STORAGE_PATH="$STORAGE_PATH" "$PROJECT_ROOT/scripts/run-web-server.sh"
