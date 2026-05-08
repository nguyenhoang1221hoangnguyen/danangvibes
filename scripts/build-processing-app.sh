#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SOURCE_DIR="${SOURCE_DIR:-}"
EVENT_SLUG="${EVENT_SLUG:-}"
EVENT_NAME="${EVENT_NAME:-}"
EVENT_DATE="${EVENT_DATE:-}"
EVENT_LOCATION="${EVENT_LOCATION:-}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/dist/events}"
INSTALL_AI="${INSTALL_AI:-0}"
ENABLE_OCR="${ENABLE_OCR:-0}"
ENABLE_FACES="${ENABLE_FACES:-0}"
FORCE="${FORCE:-0}"

usage() {
  cat <<'USAGE'
Usage:
  SOURCE_DIR=/path/to/photos \
  EVENT_SLUG=danang-marathon-2026 \
  EVENT_NAME="Da Nang Marathon 2026" \
  EVENT_DATE=2026-05-07 \
  scripts/build-processing-app.sh

Optional env:
  EVENT_LOCATION="Da Nang"
  INSTALL_AI=1        # install OCR/DeepFace/FAISS dependencies
  ENABLE_OCR=1        # requires INSTALL_AI=1 or preinstalled PaddleOCR
  ENABLE_FACES=1      # requires INSTALL_AI=1 or preinstalled DeepFace + FAISS
  OUTPUT_DIR=dist/events
  FORCE=1             # recreate existing bundle
USAGE
}

if [ -z "$SOURCE_DIR" ] || [ -z "$EVENT_SLUG" ] || [ -z "$EVENT_NAME" ] || [ -z "$EVENT_DATE" ]; then
  usage
  exit 2
fi

INSTALL_AI="$INSTALL_AI" "$PROJECT_ROOT/scripts/setup-local-env.sh"

SOURCE_DIR="$SOURCE_DIR" \
EVENT_SLUG="$EVENT_SLUG" \
EVENT_NAME="$EVENT_NAME" \
EVENT_DATE="$EVENT_DATE" \
EVENT_LOCATION="$EVENT_LOCATION" \
OUTPUT_DIR="$OUTPUT_DIR" \
ENABLE_OCR="$ENABLE_OCR" \
ENABLE_FACES="$ENABLE_FACES" \
FORCE="$FORCE" \
  "$PROJECT_ROOT/scripts/run-processing-cli.sh"

bundle_path="$OUTPUT_DIR/$EVENT_SLUG"

cat <<EOF

Processing app build complete.
Bundle: $bundle_path

Next step:
  Copy this folder to USB/SSD, then on the Web Server machine place it under:
  inbox/bundles/$EVENT_SLUG

Then open Admin UI on the Web Server machine and import it there.
EOF
