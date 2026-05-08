#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

SOURCE_DIR="${SOURCE_DIR:-}"
EVENT_SLUG="${EVENT_SLUG:-}"
EVENT_NAME="${EVENT_NAME:-}"
EVENT_DATE="${EVENT_DATE:-}"
EVENT_LOCATION="${EVENT_LOCATION:-}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/dist/events}"
ENABLE_OCR="${ENABLE_OCR:-0}"
ENABLE_FACES="${ENABLE_FACES:-0}"
FORCE="${FORCE:-0}"

usage() {
  cat <<'USAGE'
Usage:
  SOURCE_DIR=/path/to/photos EVENT_SLUG=test-event EVENT_NAME="Test Event" EVENT_DATE=2026-05-07 scripts/run-processing-cli.sh

Optional env:
  EVENT_LOCATION="Da Nang"
  OUTPUT_DIR=dist/events
  ENABLE_OCR=1        # default 0, requires PaddleOCR
  ENABLE_FACES=1      # default 0, requires DeepFace + FAISS deps
  FORCE=1             # recreate bundle output
USAGE
}

if [ -z "$SOURCE_DIR" ] || [ -z "$EVENT_SLUG" ] || [ -z "$EVENT_NAME" ] || [ -z "$EVENT_DATE" ]; then
  usage
  exit 2
fi

args=(
  -m processing_cli process
  --source "$SOURCE_DIR"
  --event-slug "$EVENT_SLUG"
  --event-name "$EVENT_NAME"
  --event-date "$EVENT_DATE"
  --output "$OUTPUT_DIR"
)

if [ -n "$EVENT_LOCATION" ]; then
  args+=(--event-location "$EVENT_LOCATION")
fi
if [ "$ENABLE_OCR" != "1" ]; then
  args+=(--skip-ocr)
fi
if [ "$ENABLE_FACES" != "1" ]; then
  args+=(--skip-faces)
fi
if [ "$FORCE" = "1" ]; then
  args+=(--force)
fi

"$PYTHON_BIN" "${args[@]}"
"$PYTHON_BIN" -m processing_cli validate --bundle "$OUTPUT_DIR/$EVENT_SLUG"
