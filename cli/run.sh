#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
PYTHON_BIN="$ROOT_DIR/.aiplanner-venv/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  sh "$SCRIPT_DIR/install.sh"
fi

"$PYTHON_BIN" -m aiplanner_cli
