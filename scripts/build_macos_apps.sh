#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="$PROJECT_DIR/scripts/macos_apps"
DEST_DIR="${1:-$HOME/Applications}"

mkdir -p "$DEST_DIR"

for app_name in "AI Investing Start API" "AI Investing Health" "AI Investing Dashboard" "AI Investing Stop API"; do
  osacompile -o "$DEST_DIR/${app_name}.app" "$SRC_DIR/${app_name}.applescript"
done

echo "Created launchers in: $DEST_DIR"
echo "- AI Investing Start API.app"
echo "- AI Investing Health.app"
echo "- AI Investing Dashboard.app"
echo "- AI Investing Stop API.app"
