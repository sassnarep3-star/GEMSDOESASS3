#!/usr/bin/env bash
# Reproducible competition & external dataset provisioning wrapper.
# Delegates to scripts/prepare_data.py, which verifies every dataset against
# pinned SHA-256 checksums in registry/data_manifest.json.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi
exec "${PYTHON_BIN}" "${SCRIPT_DIR}/prepare_data.py" "$@"
