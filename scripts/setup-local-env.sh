#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/venv}"
PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"

cd "$PROJECT_ROOT"

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r requirements.txt
if [ "${INSTALL_AI:-0}" = "1" ]; then
  "$VENV_DIR/bin/python" -m pip install -r requirements-ai.txt
fi

printf 'Local environment ready: %s\n' "$VENV_DIR"
