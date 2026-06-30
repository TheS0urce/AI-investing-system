#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

printf "Type CONFIGURE_ALPACA_LIVE to configure production credentials: "
IFS= read -r confirmation
if [[ "$confirmation" != "CONFIGURE_ALPACA_LIVE" ]]; then
  echo "NO-GO: exact confirmation phrase required" >&2
  exit 1
fi

printf "Alpaca live API key: "
IFS= read -r api_key
printf "Alpaca live secret key: "
IFS= read -rs secret_key
printf "\n"
if [[ -z "$api_key" || -z "$secret_key" ]]; then
  echo "NO-GO: key and secret are both required" >&2
  exit 1
fi

touch .env
chmod 600 .env

upsert_env() {
  local key="$1"
  local value="$2"
  local tmp
  tmp="$(mktemp)"
  if grep -q "^${key}=" .env; then
    awk -v key="$key" -v value="$value" 'BEGIN { prefix = key "=" } index($0, prefix) == 1 { print key "=" value; next } { print }' .env > "$tmp"
  else
    cat .env > "$tmp"
    printf "%s=%s\n" "$key" "$value" >> "$tmp"
  fi
  mv "$tmp" .env
}

upsert_env "BROKER_PROVIDER" "alpaca"
upsert_env "BROKER_MODE" "live"
upsert_env "BROKER_LIVE_ENABLED" "true"
upsert_env "ALPACA_LIVE_API_KEY" "$api_key"
upsert_env "ALPACA_LIVE_SECRET_KEY" "$secret_key"
upsert_env "ALPACA_LIVE_BASE_URL" "https://api.alpaca.markets"
upsert_env "AI_LIVE_EXPECTED_CAPITAL_USD" "300"
upsert_env "AI_LIVE_CAPITAL_TOLERANCE_USD" "50"
chmod 600 .env

echo "Configured separate Alpaca live credentials."
echo "No order can be submitted until live preflight passes and AUTHORIZE_BOUNDED_LIVE is accepted."
echo "Restart the API with: ./scripts/install_launch_agent.sh"
