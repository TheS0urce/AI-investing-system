#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

REQ_FILES=(requirements.txt)
if [[ -f requirements-dev.txt ]]; then
  REQ_FILES+=(requirements-dev.txt)
fi

mkdir -p .venv
if [[ ! -x .venv/bin/python ]]; then
  echo "==> Creating virtual environment"
  python3 -m venv .venv
fi

source .venv/bin/activate

DEPS_HASH_FILE=".venv/.deps_hash"
NEW_HASH="$(cat "${REQ_FILES[@]}" 2>/dev/null | shasum -a 256 | awk '{print $1}')"
OLD_HASH=""
if [[ -f "$DEPS_HASH_FILE" ]]; then
  OLD_HASH="$(cat "$DEPS_HASH_FILE")"
fi

if [[ "$NEW_HASH" != "$OLD_HASH" ]]; then
  echo "==> Dependency set changed (or first run). Installing dependencies..."
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  if [[ -f requirements-dev.txt ]]; then
    pip install -r requirements-dev.txt
  fi
  pip install streamlit requests python-dotenv slowapi uvicorn fastapi || true
  echo "$NEW_HASH" > "$DEPS_HASH_FILE"
else
  echo "==> Dependencies unchanged. Skipping reinstall."
fi

if [[ ! -f .env ]]; then
  echo "==> Creating .env with generated API key"
  KEY="$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"
  cat > .env <<EOT
AI_API_KEY=$KEY
AI_RATE_LIMIT_PER_MINUTE=60
EOT
fi

export AI_API_BASE="http://127.0.0.1:8000"
export AI_API_KEY="$(grep '^AI_API_KEY=' .env | cut -d= -f2-)"

if [[ -f ./scripts/check.sh ]]; then
  echo "==> Running validation checks"
  ./scripts/check.sh
fi

echo "==> Health/auth smoke checks"
curl -s http://127.0.0.1:8000/health || true
echo
curl -i -X POST http://127.0.0.1:8000/simulate_tick -H "Content-Type: application/json" -d '{}' || true
echo
curl -s -X POST http://127.0.0.1:8000/simulate_tick -H "Content-Type: application/json" -H "X-API-Key: $AI_API_KEY" -d '{}' || true
echo

echo "==> Dashboard endpoint check"
curl -s http://127.0.0.1:8000/dashboard/summary -H "X-API-Key: $AI_API_KEY" || true
echo

echo "==> Starting Streamlit dashboard at http://localhost:8501"
exec streamlit run dashboard.py --server.port 8501
