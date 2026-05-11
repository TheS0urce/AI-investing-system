#!/usr/bin/env bash
cd "/Users/michielburger/Claude Code/AI-investing-system"
source .venv/bin/activate
exec python -m uvicorn app:app --host 0.0.0.0 --port 8000
