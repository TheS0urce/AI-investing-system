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

if [[ "$PROVIDER" == "unset" || "$MODE" == "unset" ]]; then
  echo "PAPER-BROKER-NOT-CONFIGURED: safe for current shadow deployment"
  exit 0
fi

if [[ "$PROVIDER" != "alpaca" ]]; then
  echo "NO-GO: unsupported BROKER_PROVIDER=$PROVIDER" >&2
  exit 1
fi

case "$MODE" in
  paper)
    if [[ "$LIVE_ENABLED" != "false" ]]; then
      echo "NO-GO: paper mode requires BROKER_LIVE_ENABLED=false" >&2
      exit 1
    fi
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
  live)
    if [[ "$LIVE_ENABLED" != "true" ]]; then
      echo "LIVE-DISABLED: live mode requires BROKER_LIVE_ENABLED=true" >&2
      exit 1
    fi
    if [[ "${ALPACA_LIVE_BASE_URL:-}" != "https://api.alpaca.markets" ]]; then
      echo "LIVE-NO-GO: exact Alpaca production domain required" >&2
      exit 1
    fi
    missing=0
    for name in ALPACA_LIVE_API_KEY ALPACA_LIVE_SECRET_KEY; do
      if [[ -z "${!name:-}" || "${!name:-}" == replace_* ]]; then
        echo "missing_or_placeholder=$name"
        missing=1
      fi
    done
    if [[ "$missing" -eq 1 ]]; then
      echo "LIVE-NO-GO: add separate live credentials to local .env only"
      exit 1
    fi
    echo "ALPACA-LIVE-CONFIG-READY: API preflight and authorization still required"
    ;;
  *)
    echo "NO-GO: BROKER_MODE must be paper or live" >&2
    exit 1
    ;;
esac
