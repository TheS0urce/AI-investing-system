#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

LABEL="com.aiinvesting.live-recovery-observer"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
USER_DOMAIN="gui/$(id -u)"

if [[ ! -x .venv/bin/python || ! -f .env ]]; then
  echo "Recovery observer install requires an initialized virtualenv and .env." >&2
  exit 1
fi

set -a
source .env
set +a

API_BASE="${AI_API_BASE:-http://127.0.0.1:8001}"
if [[ -z "${AI_API_KEY:-}" ]]; then
  echo "AI_API_KEY is required." >&2
  exit 1
fi

echo "Running validation before recovery observer install"
./scripts/check.sh

READINESS="$(curl -fsS "$API_BASE/broker/live/readiness" -H "X-API-Key: $AI_API_KEY")"
.venv/bin/python -c 'import json,sys; p=json.loads(sys.argv[1]); raise SystemExit(0 if p.get("status")=="LIVE-PREFLIGHT-GO" else "live preflight is not GO")' "$READINESS"

mkdir -p "$HOME/Library/LaunchAgents" logs state
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
    <string>${PROJECT_DIR}/scripts/run_scheduled_live_recovery_observer.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${PROJECT_DIR}</string>
  <key>StartInterval</key>
  <integer>300</integer>
  <key>StandardOutPath</key>
  <string>${PROJECT_DIR}/logs/live_recovery_observer_agent.launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>${PROJECT_DIR}/logs/live_recovery_observer_agent.launchd.err.log</string>
</dict>
</plist>
PLIST

launchctl bootout "$USER_DOMAIN" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "$USER_DOMAIN" "$PLIST"
launchctl kickstart -k "${USER_DOMAIN}/${LABEL}"

echo "Live recovery observer installed: $LABEL"
