#!/usr/bin/env bash
# Create a local Python environment for this repo and install the package with dev tools.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
"$PY" -m venv .venv
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -e ".[dev]"
.venv/bin/python --version
echo "Environment ready. Activate with: source .venv/bin/activate"
