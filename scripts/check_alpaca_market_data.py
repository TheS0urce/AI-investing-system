from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ai_investing.alpaca import AlpacaMarketDataCredentials, fetch_stock_snapshot  # noqa: E402


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
    symbol = os.getenv("ALPACA_MARKET_DATA_SYMBOL", "QQQ")
    credentials = AlpacaMarketDataCredentials(
        api_key=os.getenv("ALPACA_PAPER_API_KEY", ""),
        secret_key=os.getenv("ALPACA_PAPER_SECRET_KEY", ""),
        base_url=os.getenv("ALPACA_MARKET_DATA_BASE_URL", "https://data.alpaca.markets"),
        feed=os.getenv("ALPACA_MARKET_DATA_FEED", "iex"),
    )
    try:
        snapshot = fetch_stock_snapshot(credentials, symbol=symbol)
    except Exception as exc:
        print(json.dumps({"status": "NO-GO", "reason": str(exc)}))
        return 1

    print(
        json.dumps(
            {
                "status": "ALPACA-MARKET-DATA-OK",
                "symbol": snapshot.symbol,
                "price": snapshot.price,
                "spread_bps": snapshot.spread_bps,
                "volume_24h": snapshot.volume_24h,
                "volatility_30d": snapshot.volatility_30d,
                "timestamp": snapshot.timestamp.isoformat(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
