#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8010}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/dist/events}"
CONFIG_PATH="${CONFIG_PATH:-$PROJECT_ROOT/processing_cli/config.yaml}"
INSTALL_AI="${INSTALL_AI:-1}"
VENV_DIR="${DANANGVIBES_PROCESSING_VENV_DIR:-$PROJECT_ROOT/venv-ai}"
PYTHON_BIN_FALLBACK="${PYTHON_BIN_FALLBACK:-}"

find_python_311() {
  if [ -n "$PYTHON_BIN_FALLBACK" ] && command -v "$PYTHON_BIN_FALLBACK" >/dev/null 2>&1; then
    command -v "$PYTHON_BIN_FALLBACK"
    return 0
  fi
  for candidate in python3.11 /opt/homebrew/bin/python3.11 /usr/local/bin/python3.11; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

if [ ! -x "$VENV_DIR/bin/python" ]; then
  if ! PYTHON_311_BIN="$(find_python_311)"; then
    cat <<'EOF'
Python 3.11 is required for the full OCR + DeepFace Processing Web App.
Current AI dependencies do not install reliably on Python 3.14 because TensorFlow has no matching wheel.

Install Python 3.11 once:
  brew install python@3.11

Then run only:
  scripts/start-processing-app.sh
EOF
    exit 2
  fi
else
  PYTHON_311_BIN="$VENV_DIR/bin/python"
  if ! "$PYTHON_311_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)' >/dev/null 2>&1; then
    cat <<EOF
Existing Processing AI venv is not Python 3.11: $VENV_DIR
Remove it once, then rerun:
  rm -rf "$VENV_DIR"
  scripts/start-processing-app.sh
EOF
    exit 2
  fi
fi

VENV_DIR="$VENV_DIR" PYTHON_BIN_FALLBACK="$PYTHON_311_BIN" INSTALL_AI="$INSTALL_AI" "$PROJECT_ROOT/scripts/setup-local-env.sh"
PYTHON_BIN="$VENV_DIR/bin/python"
mkdir -p "$OUTPUT_DIR"

export DANANGVIBES_PROCESSING_HOST="$HOST"
export DANANGVIBES_PROCESSING_PORT="$PORT"
export DANANGVIBES_PROCESSING_OUTPUT_ROOT="$OUTPUT_DIR"
export DANANGVIBES_PROCESSING_CONFIG_PATH="$CONFIG_PATH"

cat <<EOF

Processing Web App is starting.
Open: http://$HOST:$PORT
Output: $OUTPUT_DIR

Use the browser UI to select a local photo folder and run full OCR + face processing.
EOF

exec "$PYTHON_BIN" -m processing_web run --host "$HOST" --port "$PORT"
