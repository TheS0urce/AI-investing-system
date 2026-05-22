from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def masked_prefix(value: str) -> str | None:
    if not value:
        return None
    return f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"


def main() -> int:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ALPACA_PAPER_API_KEY", "")
    secret_key = os.getenv("ALPACA_PAPER_SECRET_KEY", "")
    payload = {
        "broker_provider": os.getenv("BROKER_PROVIDER", "unset"),
        "broker_mode": os.getenv("BROKER_MODE", "unset"),
        "broker_live_enabled": os.getenv("BROKER_LIVE_ENABLED", "false"),
        "paper_base_url": os.getenv("ALPACA_PAPER_BASE_URL", "unset"),
        "paper_api_key_present": bool(api_key),
        "paper_api_key_length": len(api_key),
        "paper_api_key_masked": masked_prefix(api_key),
        "paper_secret_key_present": bool(secret_key),
        "paper_secret_key_length": len(secret_key),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
