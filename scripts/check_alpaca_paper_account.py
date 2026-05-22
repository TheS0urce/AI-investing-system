from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ai_investing.alpaca import AlpacaPaperCredentials, fetch_paper_account  # noqa: E402


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    load_dotenv(ROOT / ".env")

    provider = os.getenv("BROKER_PROVIDER", "none").lower()
    mode = os.getenv("BROKER_MODE", "none").lower()
    live_enabled = os.getenv("BROKER_LIVE_ENABLED", "false").lower() == "true"

    if live_enabled:
        print(json.dumps({"status": "NO-GO", "reason": "live_broker_routing_disabled_for_current_stage"}))
        return 1

    if provider != "alpaca" or mode != "paper":
        print(json.dumps({"status": "SKIP", "reason": "alpaca_paper_not_configured"}))
        return 0

    api_key = os.getenv("ALPACA_PAPER_API_KEY", "")
    secret_key = os.getenv("ALPACA_PAPER_SECRET_KEY", "")
    base_url = os.getenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")

    if not api_key or not secret_key:
        print(json.dumps({"status": "NO-GO", "reason": "paper_credentials_missing"}))
        return 1

    try:
        summary = fetch_paper_account(AlpacaPaperCredentials(api_key=api_key, secret_key=secret_key, base_url=base_url))
    except RuntimeError as exc:
        print(json.dumps({"status": "NO-GO", "reason": str(exc)}))
        return 1

    print(
        json.dumps(
            {
                "status": "ALPACA-PAPER-ACCOUNT-OK",
                "account": {
                    "status": summary.status,
                    "currency": summary.currency,
                    "buying_power": summary.buying_power,
                    "cash": summary.cash,
                    "portfolio_value": summary.portfolio_value,
                    "pattern_day_trader": summary.pattern_day_trader,
                    "account_number_masked": summary.account_number_masked,
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
