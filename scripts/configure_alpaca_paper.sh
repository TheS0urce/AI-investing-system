#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

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

printf "Alpaca paper API key: "
IFS= read -r api_key
printf "Alpaca paper secret key: "
IFS= read -rs secret_key
printf "\n"

if [[ -z "$api_key" || -z "$secret_key" ]]; then
  echo "NO-GO: key and secret are both required" >&2
  exit 1
fi

upsert_env "BROKER_PROVIDER" "alpaca"
upsert_env "BROKER_MODE" "paper"
upsert_env "BROKER_LIVE_ENABLED" "false"
upsert_env "ALPACA_PAPER_API_KEY" "$api_key"
upsert_env "ALPACA_PAPER_SECRET_KEY" "$secret_key"
upsert_env "ALPACA_PAPER_BASE_URL" "https://paper-api.alpaca.markets"

chmod 600 .env

echo "Configured Alpaca paper credentials in local .env"
echo "Restart the API with: ./scripts/install_launch_agent.sh"
