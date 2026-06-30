from __future__ import annotations

from dataclasses import dataclass
import json
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .alpaca import (
    AlpacaAccountSummary,
    AlpacaPaperClock,
    AlpacaPaperOrderResult,
    AlpacaPaperPosition,
    account_summary_from_payload,
    alpaca_order_payload,
    http_error_body,
    paper_clock_from_payload,
    paper_order_result_from_payload,
    paper_orders_from_payload,
    paper_positions_from_payload,
)
from .models import OrderProposal

try:
    import certifi
except ImportError:  # pragma: no cover - optional dependency fallback
    certifi = None


@dataclass(frozen=True)
class AlpacaLiveCredentials:
    api_key: str
    secret_key: str
    base_url: str = "https://api.alpaca.markets"


def ensure_live_credentials(credentials: AlpacaLiveCredentials) -> None:
    if credentials.base_url.rstrip("/") != "https://api.alpaca.markets":
        raise RuntimeError("alpaca_live_domain_guard_failed")
    if not credentials.api_key or not credentials.secret_key:
        raise RuntimeError("alpaca_live_credentials_missing")


def _request_json(
    credentials: AlpacaLiveCredentials,
    *,
    path: str,
    error_name: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> Any:
    ensure_live_credentials(credentials)
    request = Request(
        f"{credentials.base_url.rstrip('/')}{path}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={
            "APCA-API-KEY-ID": credentials.api_key,
            "APCA-API-SECRET-KEY": credentials.secret_key,
            "Content-Type": "application/json",
        },
        method=method,
    )
    context = ssl.create_default_context(cafile=certifi.where()) if certifi else ssl.create_default_context()
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise RuntimeError(f"alpaca_live_{error_name}_http_error:{exc.code}:{http_error_body(exc)}") from exc
    except URLError as exc:
        raise RuntimeError(f"alpaca_live_{error_name}_network_error:{exc.reason}") from exc

    if not body:
        return []
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"alpaca_live_{error_name}_invalid_json") from exc


def fetch_live_account(
    credentials: AlpacaLiveCredentials,
    timeout: float = 10.0,
) -> AlpacaAccountSummary:
    payload = _request_json(
        credentials,
        path="/v2/account",
        error_name="account",
        timeout=timeout,
    )
    if not isinstance(payload, dict):
        raise RuntimeError("alpaca_live_account_invalid_payload")
    return account_summary_from_payload(payload)


def fetch_live_orders(
    credentials: AlpacaLiveCredentials,
    status: str = "all",
    limit: int = 20,
    timeout: float = 10.0,
) -> list[AlpacaPaperOrderResult]:
    if limit <= 0 or limit > 100:
        raise ValueError("limit_must_be_between_1_and_100")
    payload = _request_json(
        credentials,
        path=f"/v2/orders?status={status}&limit={limit}&direction=desc",
        error_name="orders",
        timeout=timeout,
    )
    if not isinstance(payload, list):
        raise RuntimeError("alpaca_live_orders_invalid_payload")
    return paper_orders_from_payload(payload)


def fetch_live_positions(
    credentials: AlpacaLiveCredentials,
    timeout: float = 10.0,
) -> list[AlpacaPaperPosition]:
    payload = _request_json(
        credentials,
        path="/v2/positions",
        error_name="positions",
        timeout=timeout,
    )
    if not isinstance(payload, list):
        raise RuntimeError("alpaca_live_positions_invalid_payload")
    return paper_positions_from_payload(payload)


def fetch_live_clock(
    credentials: AlpacaLiveCredentials,
    timeout: float = 10.0,
) -> AlpacaPaperClock:
    payload = _request_json(
        credentials,
        path="/v2/clock",
        error_name="clock",
        timeout=timeout,
    )
    if not isinstance(payload, dict):
        raise RuntimeError("alpaca_live_clock_invalid_payload")
    return paper_clock_from_payload(payload)


def submit_live_order(
    credentials: AlpacaLiveCredentials,
    order: OrderProposal,
    timeout: float = 10.0,
) -> AlpacaPaperOrderResult:
    payload = _request_json(
        credentials,
        path="/v2/orders",
        error_name="order",
        method="POST",
        payload=alpaca_order_payload(order),
        timeout=timeout,
    )
    if not isinstance(payload, dict):
        raise RuntimeError("alpaca_live_order_invalid_payload")
    return paper_order_result_from_payload(payload)


def cancel_live_orders(
    credentials: AlpacaLiveCredentials,
    timeout: float = 10.0,
) -> list[AlpacaPaperOrderResult]:
    payload = _request_json(
        credentials,
        path="/v2/orders",
        error_name="cancel_orders",
        method="DELETE",
        timeout=timeout,
    )
    if not isinstance(payload, list):
        raise RuntimeError("alpaca_live_cancel_orders_invalid_payload")
    orders: list[AlpacaPaperOrderResult] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        body = item.get("body")
        orders.append(
            paper_order_result_from_payload(body)
            if isinstance(body, dict)
            else AlpacaPaperOrderResult(
                broker_order_id=str(item.get("id", "")),
                client_order_id=None,
                status=str(item.get("status", "unknown")),
                symbol="",
                side="",
                submitted_at=None,
            )
        )
    return orders
