#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [[ -x .venv/bin/python ]]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

echo "==> Running tests"
"$PYTHON" -m pytest -q

echo "==> Running demo"
"$PYTHON" examples/run_demo.py

echo "==> Checking API import"
AI_API_KEY="${AI_API_KEY:-check-import-key}" "$PYTHON" -c "import app; print(app.app.title)"

echo "==> check.sh PASS"
