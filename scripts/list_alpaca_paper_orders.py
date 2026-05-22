from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ai_investing.alpaca import AlpacaPaperCredentials, fetch_paper_orders  # noqa: E402
from scripts.check_alpaca_paper_account import load_dotenv  # noqa: E402


def main() -> int:
    load_dotenv(ROOT / ".env")
    credentials = AlpacaPaperCredentials(
        api_key=os.getenv("ALPACA_PAPER_API_KEY", ""),
        secret_key=os.getenv("ALPACA_PAPER_SECRET_KEY", ""),
        base_url=os.getenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets"),
    )
    try:
        orders = fetch_paper_orders(credentials, status="all", limit=20)
    except (RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "NO-GO", "reason": str(exc)}))
        return 1

    print(
        json.dumps(
            [
                {
                    "broker_order_id": order.broker_order_id,
                    "client_order_id": order.client_order_id,
                    "status": order.status,
                    "symbol": order.symbol,
                    "side": order.side,
                    "submitted_at": order.submitted_at,
                }
                for order in orders
            ],
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
