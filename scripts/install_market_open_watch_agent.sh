#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

LABEL="com.aiinvesting.market-open-watch"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
USER_DOMAIN="gui/$(id -u)"
PREAUTHORIZED_SUBMIT_ARG=""

if [[ "${1:-}" == "--preauthorized-submit" ]]; then
  PREAUTHORIZED_SUBMIT_ARG="    <string>--preauthorized-submit</string>"
elif [[ -n "${1:-}" ]]; then
  echo "Usage: $0 [--preauthorized-submit]" >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" logs state

if [[ ! -x .venv/bin/python ]]; then
  echo "Missing .venv. Run ./scripts/launch_dashboard.sh once first." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Missing .env. Run ./scripts/install_launch_agent.sh first." >&2
  exit 1
fi

echo "Running validation before market-open watch install"
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
    <string>${PROJECT_DIR}/.venv/bin/python</string>
    <string>${PROJECT_DIR}/scripts/run_scheduled_market_open_watch.py</string>
${PREAUTHORIZED_SUBMIT_ARG}
  </array>
  <key>WorkingDirectory</key>
  <string>${PROJECT_DIR}</string>
  <key>StartInterval</key>
  <integer>300</integer>
  <key>StandardOutPath</key>
  <string>${PROJECT_DIR}/logs/market_open_watch_agent.launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>${PROJECT_DIR}/logs/market_open_watch_agent.launchd.err.log</string>
</dict>
</plist>
PLIST

launchctl bootout "$USER_DOMAIN" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "$USER_DOMAIN" "$PLIST"
launchctl kickstart -k "${USER_DOMAIN}/${LABEL}"

echo "LaunchAgent installed: $LABEL"
if [[ -n "$PREAUTHORIZED_SUBMIT_ARG" ]]; then
  echo "Mode: bounded preauthorized paper submit"
else
  echo "Mode: read-only paper watch"
fi
echo "Plist: $PLIST"
echo "Log: ${PROJECT_DIR}/logs/market_open_watch_agent.log"
