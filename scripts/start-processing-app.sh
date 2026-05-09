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

find_python3() {
  if [ -n "$PYTHON_BIN_FALLBACK" ] && command -v "$PYTHON_BIN_FALLBACK" >/dev/null 2>&1; then
    command -v "$PYTHON_BIN_FALLBACK"
    return 0
  fi
  # Prefer versions known to work with AI deps (TensorFlow), then fall back to any python3
  for candidate in python3.11 python3.12 python3.10 python3 \
    /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.10 /opt/homebrew/bin/python3 \
    /usr/local/bin/python3.11 /usr/local/bin/python3.12 /usr/local/bin/python3.10 /usr/local/bin/python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

if [ ! -x "$VENV_DIR/bin/python" ]; then
  if ! PYTHON3_BIN="$(find_python3)"; then
    cat <<'EOF'
Python 3 is required for the Processing Web App.
No python3 found on PATH.

Install Python 3:
  brew install python@3.12

Then run:
  scripts/start-processing-app.sh
EOF
    exit 2
  fi
else
  PYTHON3_BIN="$VENV_DIR/bin/python"
  if ! "$PYTHON3_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
    PYVER=$("$PYTHON3_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    cat <<EOF
Existing Processing AI venv uses Python $PYVER, which may be too old.
Remove it and rerun:
  rm -rf "$VENV_DIR"
  scripts/start-processing-app.sh
EOF
    exit 2
  fi
fi

VENV_DIR="$VENV_DIR" PYTHON_BIN_FALLBACK="$PYTHON3_BIN" INSTALL_AI="$INSTALL_AI" "$PROJECT_ROOT/scripts/setup-local-env.sh"
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
