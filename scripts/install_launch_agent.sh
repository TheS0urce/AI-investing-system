#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

LABEL="com.aiinvesting.api"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
USER_DOMAIN="gui/$(id -u)"

mkdir -p "$HOME/Library/LaunchAgents" logs

if [[ ! -x .venv/bin/python ]]; then
  echo "Missing .venv. Run ./scripts/launch_dashboard.sh once first." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Creating local .env"
  KEY="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))')"
  {
    echo "AI_API_KEY=$KEY"
    echo "AI_RATE_LIMIT_PER_MINUTE=60"
    echo "AI_API_HOST=127.0.0.1"
    echo "AI_API_PORT=8001"
  } > .env
fi

if ! grep -q '^AI_API_HOST=' .env; then
  echo "AI_API_HOST=127.0.0.1" >> .env
fi

if ! grep -q '^AI_API_PORT=' .env; then
  echo "AI_API_PORT=8001" >> .env
fi

echo "Running validation before install"
./scripts/check.sh

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PROJECT_DIR}/run_server.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${PROJECT_DIR}</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${PROJECT_DIR}/logs/api.launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>${PROJECT_DIR}/logs/api.launchd.err.log</string>
</dict>
</plist>
PLIST

launchctl bootout "$USER_DOMAIN" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "$USER_DOMAIN" "$PLIST"
launchctl kickstart -k "${USER_DOMAIN}/${LABEL}"

set -a
source .env
set +a

API_BASE="http://${AI_API_HOST:-127.0.0.1}:${AI_API_PORT:-8001}"
echo "Waiting for API at $API_BASE"
for _ in {1..30}; do
  if curl -fsS "$API_BASE/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

curl -fsS "$API_BASE/health"
echo
curl -fsS "$API_BASE/dashboard/summary" -H "X-API-Key: $AI_API_KEY"
echo
curl -fsS "$API_BASE/broker/status" -H "X-API-Key: $AI_API_KEY"
echo

echo "LaunchAgent installed: $LABEL"
echo "Plist: $PLIST"
