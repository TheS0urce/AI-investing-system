#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

API_HOST="${AI_API_HOST:-127.0.0.1}"
API_PORT="${AI_API_PORT:-8001}"
API_BASE="http://${API_HOST}:${API_PORT}"

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
  echo "==> Installing dependencies"
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  if [[ -f requirements-dev.txt ]]; then
    python -m pip install -r requirements-dev.txt
  fi
  python -m pip install fastapi uvicorn slowapi python-dotenv streamlit requests
  echo "$NEW_HASH" > "$DEPS_HASH_FILE"
else
  echo "==> Dependencies unchanged"
fi

if [[ ! -f .env ]]; then
  echo "==> Creating local .env"
  KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
  {
    echo "AI_API_KEY=$KEY"
    echo "AI_RATE_LIMIT_PER_MINUTE=60"
  } > .env
fi

set -a
source .env
set +a

export AI_API_BASE="$API_BASE"
export AI_API_KEY
export AI_RATE_LIMIT_PER_MINUTE="${AI_RATE_LIMIT_PER_MINUTE:-60}"

echo "==> Running validation checks"
./scripts/check.sh

API_PID=""
if curl -fsS "$API_BASE/health" >/dev/null 2>&1; then
  echo "==> API already running at $API_BASE"
  AUTH_STATUS="$(curl -s -o /dev/null -w '%{http_code}' "$API_BASE/dashboard/summary" -H "X-API-Key: $AI_API_KEY")"
  if [[ "$AUTH_STATUS" != "200" ]]; then
    echo "Existing API rejected the key from .env." >&2
    echo "Stop the existing API process, then rerun ./scripts/launch_dashboard.sh." >&2
    echo "If you intentionally want to keep it running, restart this launcher with the same AI_API_KEY." >&2
    exit 1
  fi
else
  echo "==> Starting API at $API_BASE"
  python -m uvicorn app:app --host "$API_HOST" --port "$API_PORT" &
  API_PID="$!"

  for _ in {1..30}; do
    if curl -fsS "$API_BASE/health" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

cleanup() {
  if [[ -n "$API_PID" ]]; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "==> Health/auth smoke checks"
curl -fsS "$API_BASE/health"
echo

UNAUTH_STATUS="$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API_BASE/simulate_tick" -H "Content-Type: application/json" -d '{}')"
if [[ "$UNAUTH_STATUS" != "401" ]]; then
  echo "Expected unauthenticated /simulate_tick to return 401, got $UNAUTH_STATUS" >&2
  exit 1
fi
echo "Unauthenticated simulate_tick returned 401"

curl -fsS -X POST "$API_BASE/simulate_tick" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $AI_API_KEY" \
  -d '{"cash":100,"equity":100,"peak_equity":100,"daily_pnl":0}'
echo

curl -fsS "$API_BASE/dashboard/summary" -H "X-API-Key: $AI_API_KEY"
echo

echo "==> Starting Streamlit dashboard at http://localhost:8501"
python -m streamlit run dashboard.py --server.port 8501
