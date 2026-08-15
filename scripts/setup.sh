#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
mkdir -p data downloads cache
echo "Setup complete. Run: ./.venv/bin/python run.py"
