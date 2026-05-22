from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json
import ssl

try:
    import certifi
except ImportError:  # pragma: no cover - optional dependency fallback
    certifi = None


@dataclass(frozen=True)
class AlpacaPaperCredentials:
    api_key: str
    secret_key: str
    base_url: str = "https://paper-api.alpaca.markets"


@dataclass(frozen=True)
class AlpacaAccountSummary:
    status: str
    currency: str
    buying_power: str
    cash: str
    portfolio_value: str
    pattern_day_trader: bool
    account_number_masked: str | None


def mask_account_number(account_number: str | None) -> str | None:
    if not account_number:
        return None
    if len(account_number) <= 4:
        return "*" * len(account_number)
    return f"{'*' * (len(account_number) - 4)}{account_number[-4:]}"


def decimal_string(value: Any) -> str:
    try:
        return str(Decimal(str(value)))
    except (InvalidOperation, ValueError):
        return "0"


def account_summary_from_payload(payload: dict[str, Any]) -> AlpacaAccountSummary:
    return AlpacaAccountSummary(
        status=str(payload.get("status", "unknown")),
        currency=str(payload.get("currency", "unknown")),
        buying_power=decimal_string(payload.get("buying_power", "0")),
        cash=decimal_string(payload.get("cash", "0")),
        portfolio_value=decimal_string(payload.get("portfolio_value", "0")),
        pattern_day_trader=bool(payload.get("pattern_day_trader", False)),
        account_number_masked=mask_account_number(payload.get("account_number")),
    )


def fetch_paper_account(credentials: AlpacaPaperCredentials, timeout: float = 10.0) -> AlpacaAccountSummary:
    request = Request(
        f"{credentials.base_url.rstrip('/')}/v2/account",
        headers={
            "APCA-API-KEY-ID": credentials.api_key,
            "APCA-API-SECRET-KEY": credentials.secret_key,
        },
    )
    context = ssl.create_default_context(cafile=certifi.where()) if certifi else ssl.create_default_context()
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"alpaca_account_http_error:{exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"alpaca_account_network_error:{exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("alpaca_account_invalid_json") from exc

    return account_summary_from_payload(payload)
