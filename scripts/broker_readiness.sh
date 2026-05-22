#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

PROVIDER="${BROKER_PROVIDER:-unset}"
MODE="${BROKER_MODE:-unset}"
LIVE_ENABLED="${BROKER_LIVE_ENABLED:-false}"

echo "broker_provider=$PROVIDER"
echo "broker_mode=$MODE"
echo "broker_live_enabled=$LIVE_ENABLED"

if [[ "$LIVE_ENABLED" != "false" ]]; then
  echo "NO-GO: BROKER_LIVE_ENABLED must remain false for this stage" >&2
  exit 1
fi

if [[ "$PROVIDER" == "unset" || "$MODE" == "unset" ]]; then
  echo "PAPER-BROKER-NOT-CONFIGURED: safe for current shadow deployment"
  exit 0
fi

if [[ "$MODE" != "paper" ]]; then
  echo "NO-GO: BROKER_MODE must be paper for Stage-1 integration" >&2
  exit 1
fi

case "$PROVIDER" in
  alpaca)
    missing=0
    for name in ALPACA_PAPER_API_KEY ALPACA_PAPER_SECRET_KEY ALPACA_PAPER_BASE_URL; do
      if [[ -z "${!name:-}" || "${!name:-}" == "replace_me" ]]; then
        echo "missing_or_placeholder=$name"
        missing=1
      fi
    done
    if [[ "$missing" -eq 1 ]]; then
      echo "ALPACA-PAPER-NOT-READY: add paper credentials to local .env only"
      exit 0
    fi
    echo "ALPACA-PAPER-READY: credentials are present locally"
    ;;
  *)
    echo "NO-GO: unsupported BROKER_PROVIDER=$PROVIDER" >&2
    exit 1
    ;;
esac
