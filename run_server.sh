#!/usr/bin/env bash
cd "/Users/michielburger/Claude Code/AI-investing-system"
source .venv/bin/activate
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi
exec python -m uvicorn app:app --host "${AI_API_HOST:-127.0.0.1}" --port "${AI_API_PORT:-8001}"
