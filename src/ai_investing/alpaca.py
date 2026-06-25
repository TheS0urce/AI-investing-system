from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json
import ssl

from .models import MarketSnapshot, OrderProposal, Side

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
class AlpacaMarketDataCredentials:
    api_key: str
    secret_key: str
    base_url: str = "https://data.alpaca.markets"
    feed: str = "iex"


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


@dataclass(frozen=True)
class AlpacaPaperPosition:
    symbol: str
    quantity: float
    market_value: float
    avg_entry_price: float
    current_price: float


@dataclass(frozen=True)
class AlpacaPaperClock:
    timestamp: str
    is_open: bool
    next_open: str
    next_close: str


ALLOWED_MARKET_DATA_FEEDS = {"iex", "sip", "delayed_sip", "boats", "overnight", "otc"}


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


def ensure_market_data_credentials(credentials: AlpacaMarketDataCredentials) -> None:
    if credentials.base_url.rstrip("/") != "https://data.alpaca.markets":
        raise RuntimeError("alpaca_market_data_guard_failed")
    if not credentials.api_key or not credentials.secret_key:
        raise RuntimeError("alpaca_market_data_credentials_missing")
    if credentials.feed not in ALLOWED_MARKET_DATA_FEEDS:
        raise RuntimeError("alpaca_market_data_feed_not_allowed")


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


def alpaca_bracket_order_payload(
    order: OrderProposal,
    *,
    stop_price: float,
    take_profit_price: float,
) -> dict[str, Any]:
    if order.side != Side.BUY:
        raise ValueError("bracket_entry_must_be_buy")
    if stop_price <= 0 or take_profit_price <= 0:
        raise ValueError("bracket_exit_prices_must_be_positive")
    if not stop_price < order.limit_price < take_profit_price:
        raise ValueError("bracket_exit_prices_must_bound_entry")

    return {
        **alpaca_order_payload(order),
        "order_class": "bracket",
        "take_profit": {"limit_price": f"{take_profit_price:.2f}"},
        "stop_loss": {"stop_price": f"{stop_price:.2f}"},
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


def paper_position_from_payload(payload: dict[str, Any]) -> AlpacaPaperPosition:
    return AlpacaPaperPosition(
        symbol=str(payload.get("symbol", "")).upper(),
        quantity=float(decimal_string(payload.get("qty", 0))),
        market_value=float(decimal_string(payload.get("market_value", 0))),
        avg_entry_price=float(decimal_string(payload.get("avg_entry_price", 0))),
        current_price=float(decimal_string(payload.get("current_price", 0))),
    )


def paper_positions_from_payload(payload: list[dict[str, Any]]) -> list[AlpacaPaperPosition]:
    return [paper_position_from_payload(item) for item in payload]


def paper_clock_from_payload(payload: dict[str, Any]) -> AlpacaPaperClock:
    return AlpacaPaperClock(
        timestamp=str(payload.get("timestamp", "")),
        is_open=bool(payload.get("is_open", False)),
        next_open=str(payload.get("next_open", "")),
        next_close=str(payload.get("next_close", "")),
    )


def parse_alpaca_time(value: Any) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def market_snapshot_from_alpaca_payload(
    symbol: str,
    payload: dict[str, Any],
    default_volatility_30d: float = 0.03,
) -> MarketSnapshot:
    latest_trade = payload.get("latestTrade") if isinstance(payload.get("latestTrade"), dict) else {}
    latest_quote = payload.get("latestQuote") if isinstance(payload.get("latestQuote"), dict) else {}
    daily_bar = payload.get("dailyBar") if isinstance(payload.get("dailyBar"), dict) else {}
    minute_bar = payload.get("minuteBar") if isinstance(payload.get("minuteBar"), dict) else {}

    bid = float(decimal_string(latest_quote.get("bp", 0)))
    ask = float(decimal_string(latest_quote.get("ap", 0)))
    trade_price = float(decimal_string(latest_trade.get("p", 0)))
    bar_close = float(decimal_string(minute_bar.get("c", 0)))
    daily_open = float(decimal_string(daily_bar.get("o", 0)))

    midpoint = (bid + ask) / 2 if bid > 0 and ask > 0 else 0.0
    price = trade_price or midpoint or bar_close
    if price <= 0:
        raise RuntimeError("alpaca_market_data_missing_price")

    spread_bps = ((ask - bid) / midpoint * 10_000) if bid > 0 and ask > 0 and midpoint > 0 else 0.0
    volume_24h = float(decimal_string(daily_bar.get("v", 0)))
    intraday_change_bps = ((price - daily_open) / daily_open * 10_000) if daily_open > 0 else 0.0
    timestamp = parse_alpaca_time(latest_trade.get("t") or latest_quote.get("t") or minute_bar.get("t"))

    return MarketSnapshot(
        symbol=symbol.upper(),
        price=price,
        spread_bps=spread_bps,
        volume_24h=volume_24h,
        volatility_30d=default_volatility_30d,
        timestamp=timestamp,
        intraday_change_bps=intraday_change_bps,
    )


def fetch_stock_snapshot(
    credentials: AlpacaMarketDataCredentials,
    symbol: str,
    default_volatility_30d: float = 0.03,
    timeout: float = 10.0,
) -> MarketSnapshot:
    ensure_market_data_credentials(credentials)
    clean_symbol = symbol.strip().upper()
    if not clean_symbol:
        raise ValueError("symbol_required")

    query = urlencode({"feed": credentials.feed})
    request = Request(
        f"{credentials.base_url.rstrip('/')}/v2/stocks/{clean_symbol}/snapshot?{query}",
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
        raise RuntimeError(f"alpaca_market_data_http_error:{exc.code}:{http_error_body(exc)}") from exc
    except URLError as exc:
        raise RuntimeError(f"alpaca_market_data_network_error:{exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("alpaca_market_data_invalid_json") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("alpaca_market_data_invalid_payload")
    return market_snapshot_from_alpaca_payload(clean_symbol, payload, default_volatility_30d)


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


def fetch_paper_positions(
    credentials: AlpacaPaperCredentials,
    timeout: float = 10.0,
) -> list[AlpacaPaperPosition]:
    ensure_paper_credentials(credentials)
    request = Request(
        f"{credentials.base_url.rstrip('/')}/v2/positions",
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
        raise RuntimeError(f"alpaca_positions_http_error:{exc.code}:{http_error_body(exc)}") from exc
    except URLError as exc:
        raise RuntimeError(f"alpaca_positions_network_error:{exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("alpaca_positions_invalid_json") from exc

    if not isinstance(payload, list):
        raise RuntimeError("alpaca_positions_invalid_payload")
    return paper_positions_from_payload(payload)


def fetch_paper_clock(credentials: AlpacaPaperCredentials, timeout: float = 10.0) -> AlpacaPaperClock:
    ensure_paper_credentials(credentials)
    request = Request(
        f"{credentials.base_url.rstrip('/')}/v2/clock",
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
        raise RuntimeError(f"alpaca_clock_http_error:{exc.code}:{http_error_body(exc)}") from exc
    except URLError as exc:
        raise RuntimeError(f"alpaca_clock_network_error:{exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("alpaca_clock_invalid_json") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("alpaca_clock_invalid_payload")
    return paper_clock_from_payload(payload)


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


def submit_paper_bracket_order(
    credentials: AlpacaPaperCredentials,
    order: OrderProposal,
    *,
    stop_price: float,
    take_profit_price: float,
    timeout: float = 10.0,
) -> AlpacaPaperOrderResult:
    ensure_paper_credentials(credentials)
    request = Request(
        f"{credentials.base_url.rstrip('/')}/v2/orders",
        data=json.dumps(
            alpaca_bracket_order_payload(
                order,
                stop_price=stop_price,
                take_profit_price=take_profit_price,
            )
        ).encode("utf-8"),
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
