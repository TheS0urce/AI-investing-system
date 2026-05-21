#!/usr/bin/env bash
set -euo pipefail

LABEL="com.aiinvesting.api"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
USER_DOMAIN="gui/$(id -u)"

launchctl bootout "$USER_DOMAIN" "$PLIST" >/dev/null 2>&1 || true
rm -f "$PLIST"

echo "LaunchAgent removed: $LABEL"
