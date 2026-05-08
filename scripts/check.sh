#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -f requirements.txt ]; then
  echo "ERROR: requirements.txt not found. Run from project repo."
  exit 1
fi

echo "==> Running tests"
pytest

echo "==> Running demo"
python examples/run_demo.py
