from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json
import ssl

from .models import OrderProposal

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


@dataclass(frozen=True)
class AlpacaPaperOrderResult:
    broker_order_id: str
    client_order_id: str | None
    status: str
    symbol: str
    side: str
    submitted_at: str | None


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


def ensure_paper_credentials(credentials: AlpacaPaperCredentials) -> None:
    if credentials.base_url.rstrip("/") != "https://paper-api.alpaca.markets":
        raise RuntimeError("alpaca_paper_only_guard_failed")
    if not credentials.api_key or not credentials.secret_key:
        raise RuntimeError("alpaca_paper_credentials_missing")


def alpaca_order_payload(order: OrderProposal) -> dict[str, str | bool]:
    if order.quantity <= 0:
        raise ValueError("order_quantity_must_be_positive")
    if order.limit_price <= 0:
        raise ValueError("order_limit_price_must_be_positive")

    return {
        "symbol": order.symbol,
        "qty": f"{order.quantity:.8f}".rstrip("0").rstrip("."),
        "side": order.side.value.lower(),
        "type": "limit",
        "time_in_force": "day",
        "limit_price": f"{order.limit_price:.2f}",
        "extended_hours": False,
    }


def paper_order_result_from_payload(payload: dict[str, Any]) -> AlpacaPaperOrderResult:
    return AlpacaPaperOrderResult(
        broker_order_id=str(payload.get("id", "")),
        client_order_id=payload.get("client_order_id"),
        status=str(payload.get("status", "unknown")),
        symbol=str(payload.get("symbol", "")),
        side=str(payload.get("side", "")),
        submitted_at=payload.get("submitted_at"),
    )


def paper_orders_from_payload(payload: list[dict[str, Any]]) -> list[AlpacaPaperOrderResult]:
    return [paper_order_result_from_payload(item) for item in payload]


def fetch_paper_account(credentials: AlpacaPaperCredentials, timeout: float = 10.0) -> AlpacaAccountSummary:
    ensure_paper_credentials(credentials)
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
        raise RuntimeError(f"alpaca_account_http_error:{exc.code}:{http_error_body(exc)}") from exc
    except URLError as exc:
        raise RuntimeError(f"alpaca_account_network_error:{exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("alpaca_account_invalid_json") from exc

    return account_summary_from_payload(payload)


def fetch_paper_orders(
    credentials: AlpacaPaperCredentials,
    status: str = "all",
    limit: int = 20,
    timeout: float = 10.0,
) -> list[AlpacaPaperOrderResult]:
    ensure_paper_credentials(credentials)
    if limit <= 0 or limit > 100:
        raise ValueError("limit_must_be_between_1_and_100")
    request = Request(
        f"{credentials.base_url.rstrip('/')}/v2/orders?status={status}&limit={limit}&direction=desc",
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
        raise RuntimeError(f"alpaca_orders_http_error:{exc.code}:{http_error_body(exc)}") from exc
    except URLError as exc:
        raise RuntimeError(f"alpaca_orders_network_error:{exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("alpaca_orders_invalid_json") from exc

    if not isinstance(payload, list):
        raise RuntimeError("alpaca_orders_invalid_payload")
    return paper_orders_from_payload(payload)


def cancel_paper_orders(credentials: AlpacaPaperCredentials, timeout: float = 10.0) -> list[AlpacaPaperOrderResult]:
    ensure_paper_credentials(credentials)
    request = Request(
        f"{credentials.base_url.rstrip('/')}/v2/orders",
        headers={
            "APCA-API-KEY-ID": credentials.api_key,
            "APCA-API-SECRET-KEY": credentials.secret_key,
        },
        method="DELETE",
    )
    context = ssl.create_default_context(cafile=certifi.where()) if certifi else ssl.create_default_context()
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            body = response.read().decode("utf-8")
            payload = json.loads(body) if body else []
    except HTTPError as exc:
        raise RuntimeError(f"alpaca_cancel_orders_http_error:{exc.code}:{http_error_body(exc)}") from exc
    except URLError as exc:
        raise RuntimeError(f"alpaca_cancel_orders_network_error:{exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("alpaca_cancel_orders_invalid_json") from exc

    if not isinstance(payload, list):
        raise RuntimeError("alpaca_cancel_orders_invalid_payload")
    orders: list[AlpacaPaperOrderResult] = []
    for item in payload:
        if isinstance(item, dict):
            body = item.get("body")
            if isinstance(body, dict):
                orders.append(paper_order_result_from_payload(body))
            else:
                orders.append(
                    AlpacaPaperOrderResult(
                        broker_order_id=str(item.get("id", "")),
                        client_order_id=None,
                        status=str(item.get("status", "unknown")),
                        symbol="",
                        side="",
                        submitted_at=None,
                    )
                )
    return orders


def submit_paper_order(
    credentials: AlpacaPaperCredentials,
    order: OrderProposal,
    timeout: float = 10.0,
) -> AlpacaPaperOrderResult:
    ensure_paper_credentials(credentials)
    request = Request(
        f"{credentials.base_url.rstrip('/')}/v2/orders",
        data=json.dumps(alpaca_order_payload(order)).encode("utf-8"),
        headers={
            "APCA-API-KEY-ID": credentials.api_key,
            "APCA-API-SECRET-KEY": credentials.secret_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    context = ssl.create_default_context(cafile=certifi.where()) if certifi else ssl.create_default_context()
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"alpaca_order_http_error:{exc.code}:{http_error_body(exc)}") from exc
    except URLError as exc:
        raise RuntimeError(f"alpaca_order_network_error:{exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("alpaca_order_invalid_json") from exc

    return paper_order_result_from_payload(payload)


def http_error_body(exc: HTTPError) -> str:
    try:
        return exc.read().decode("utf-8")[:500]
    except Exception:
        return ""
