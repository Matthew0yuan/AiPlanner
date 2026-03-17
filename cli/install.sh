#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
VENV_DIR="$ROOT_DIR/.aiplanner-venv"
PYTHON_BIN="$VENV_DIR/bin/python"
TMPDIR="$ROOT_DIR/.aiplanner-tmp"

if [ ! -x "$PYTHON_BIN" ]; then
  python3 -m venv "$VENV_DIR"
fi

if [ ! -x "$VENV_DIR/bin/pip" ]; then
  python3 -m venv --clear "$VENV_DIR"
fi
mkdir -p "$TMPDIR"
export TMPDIR
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -e "$ROOT_DIR"
