#!/usr/bin/env bash
# Autonomous Competition Data Placement & SHA-256 Verification Script
# Restores competition rasters, external USGS/DOE layers, and historical scored rasters
# into GEMS_DATA_DIR (defaulting to .cache/gems_data) and writes data/restore_receipt.json.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${GEMS_DATA_DIR:-$ROOT/.cache/gems_data}"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi

mkdir -p "$TARGET_DIR" "$ROOT/data"
echo "[GEMSDOESASS3] Verifying and restoring competition data into: $TARGET_DIR"
PYTHONPATH="$ROOT/src" "$PY" "$ROOT/scripts/restore_data.py" --group all --target-dir "$TARGET_DIR"
echo "[GEMSDOESASS3] Competition data placement and SHA-256 verification succeeded."
