#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="$PROJECT_DIR/scripts/macos_apps"
DEST_DIR="${1:-$HOME/Applications/AI Investment}"

mkdir -p "$DEST_DIR"

for app_name in "AI Investing Start API" "AI Investing Health" "AI Investing Dashboard" "AI Investing Daily Ops" "AI Investing Stop API"; do
  osacompile -o "$DEST_DIR/${app_name}.app" "$SRC_DIR/${app_name}.applescript"
done

if [[ -x "$PROJECT_DIR/.venv/bin/python" ]]; then
  "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/scripts/generate_macos_icons.py" "$DEST_DIR"
else
  python3 "$PROJECT_DIR/scripts/generate_macos_icons.py" "$DEST_DIR"
fi

echo "Created launchers in: $DEST_DIR"
echo "- AI Investing Start API.app"
echo "- AI Investing Health.app"
echo "- AI Investing Dashboard.app"
echo "- AI Investing Daily Ops.app"
echo "- AI Investing Stop API.app"
