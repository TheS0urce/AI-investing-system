import os
import json
import csv
import io
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse
from fastapi.responses import Response

from src.ai_investing.alpaca import (
    AlpacaAccountSummary,
    AlpacaMarketDataCredentials,
    AlpacaPaperCredentials,
    alpaca_order_payload,
    cancel_paper_orders,
    fetch_paper_account,
    fetch_stock_snapshot,
    fetch_paper_orders,
    submit_paper_order,
)
from src.ai_investing.broker import broker_readiness
from src.ai_investing.config import SystemConfig
from src.ai_investing.models import MarketSnapshot, OrderProposal, PortfolioState, Side
from src.ai_investing.strategy import SimpleMomentumStrategy
from src.ai_investing.system import InvestingSystem

load_dotenv()

app = FastAPI(title="AI Investing System", version="0.2.1")

DEFAULT_RATE = os.getenv("AI_RATE_LIMIT_PER_MINUTE", "60")
WATCH_HISTORY_PATH = Path(os.getenv("AI_WATCH_HISTORY_PATH", "logs/paper_watch_history.jsonl"))

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{DEFAULT_RATE}/minute"])
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})


config = SystemConfig(
    broker={
        "provider": os.getenv("BROKER_PROVIDER", "none"),
        "mode": os.getenv("BROKER_MODE", "none"),
        "live_enabled": os.getenv("BROKER_LIVE_ENABLED", "false").lower() == "true",
        "paper_base_url": os.getenv("ALPACA_PAPER_BASE_URL"),
        "market_data_base_url": os.getenv("ALPACA_MARKET_DATA_BASE_URL", "https://data.alpaca.markets"),
        "market_data_feed": os.getenv("ALPACA_MARKET_DATA_FEED", "iex"),
        "paper_api_key_present": bool(os.getenv("ALPACA_PAPER_API_KEY")),
        "paper_secret_key_present": bool(os.getenv("ALPACA_PAPER_SECRET_KEY")),
    }
)
strategy = SimpleMomentumStrategy()
system = InvestingSystem(config=config, strategy=strategy)


class TickRequest(BaseModel):
    symbol: str = "QQQ"
    price: float = Field(default=430.0, gt=0)
    spread_bps: float = Field(default=8.0, ge=0)
    volume_24h: float = Field(default=5_000_000.0, ge=0)
    volatility_30d: float = Field(default=0.03, ge=0)

    cash: float = 1_000.0
    equity: float = 1_000.0
    peak_equity: float = 1_050.0
    daily_pnl: float = -5.0
    consecutive_losses: int = 1


class PaperOrderPreviewRequest(BaseModel):
    symbol: str = "QQQ"
    side: Side = Side.BUY
    quantity: float = Field(gt=0)
    limit_price: float = Field(gt=0)
    expected_edge_bps: float = 0.0
    reason: str = "manual paper preview"


class PaperOrderSubmitRequest(PaperOrderPreviewRequest):
    confirm: str


class PaperCancelRequest(BaseModel):
    confirm: str


class PaperWatchTickRequest(BaseModel):
    symbol: str = "QQQ"
    feed: str | None = None
    use_paper_account: bool = True
    cash: float = 1_000.0
    equity: float = 1_000.0
    peak_equity: float = 1_000.0
    daily_pnl: float = 0.0
    consecutive_losses: int = 0


def serialize_market(market: MarketSnapshot):
    return {
        "symbol": market.symbol,
        "price": market.price,
        "spread_bps": market.spread_bps,
        "volume_24h": market.volume_24h,
        "volatility_30d": market.volatility_30d,
        "timestamp": market.timestamp.isoformat(),
    }


def serialize_order(order: OrderProposal | None):
    if order is None:
        return None
    return {
        "symbol": order.symbol,
        "side": str(order.side.value),
        "quantity": order.quantity,
        "limit_price": order.limit_price,
        "expected_edge_bps": order.expected_edge_bps,
        "reason": order.reason,
    }


def serialize_account(account: AlpacaAccountSummary):
    return {
        "status": account.status,
        "currency": account.currency,
        "buying_power": account.buying_power,
        "cash": account.cash,
        "portfolio_value": account.portfolio_value,
        "pattern_day_trader": account.pattern_day_trader,
        "account_number_masked": account.account_number_masked,
    }


def alpaca_paper_credentials() -> AlpacaPaperCredentials:
    return AlpacaPaperCredentials(
        api_key=os.getenv("ALPACA_PAPER_API_KEY", ""),
        secret_key=os.getenv("ALPACA_PAPER_SECRET_KEY", ""),
        base_url=os.getenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets"),
    )


def alpaca_market_data_credentials(feed: str | None = None) -> AlpacaMarketDataCredentials:
    return AlpacaMarketDataCredentials(
        api_key=os.getenv("ALPACA_PAPER_API_KEY", ""),
        secret_key=os.getenv("ALPACA_PAPER_SECRET_KEY", ""),
        base_url=os.getenv("ALPACA_MARKET_DATA_BASE_URL", "https://data.alpaca.markets"),
        feed=feed or os.getenv("ALPACA_MARKET_DATA_FEED", "iex"),
    )


def portfolio_from_account(account: AlpacaAccountSummary, consecutive_losses: int = 0) -> PortfolioState:
    equity = float(account.portfolio_value)
    cash = float(account.cash)
    return PortfolioState(
        cash=cash,
        equity=equity,
        peak_equity=equity,
        daily_pnl=0.0,
        consecutive_losses=consecutive_losses,
        positions={},
    )


def require_api_key(x_api_key: str | None):
    expected = os.getenv("AI_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="api_key_not_configured")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="invalid api key")


def latest_audit_payload():
    if not system.audit_log:
        return None
    latest = system.audit_log[-1]
    return {
        "at": latest.at.isoformat(),
        "event": latest.event,
        "severity": latest.severity,
        "details": latest.details,
    }


def append_watch_event(event: dict):
    WATCH_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with WATCH_HISTORY_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")


def read_watch_events(limit: int) -> list[dict]:
    if not WATCH_HISTORY_PATH.exists():
        return []
    events: list[dict] = []
    with WATCH_HISTORY_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                events.append(payload)
    return events[-limit:]


def flatten_watch_event(event: dict) -> dict[str, object]:
    market = event.get("market") if isinstance(event.get("market"), dict) else {}
    latest_audit = event.get("latest_audit") if isinstance(event.get("latest_audit"), dict) else {}
    order = event.get("order_proposal") if isinstance(event.get("order_proposal"), dict) else {}
    return {
        "at": event.get("at"),
        "symbol": event.get("symbol"),
        "feed": event.get("feed"),
        "auto_submit_enabled": event.get("auto_submit_enabled"),
        "portfolio_source": event.get("portfolio_source"),
        "market_price": market.get("price"),
        "market_spread_bps": market.get("spread_bps"),
        "market_volume_24h": market.get("volume_24h"),
        "market_volatility_30d": market.get("volatility_30d"),
        "market_timestamp": market.get("timestamp"),
        "order_symbol": order.get("symbol"),
        "order_side": order.get("side"),
        "order_quantity": order.get("quantity"),
        "order_limit_price": order.get("limit_price"),
        "order_expected_edge_bps": order.get("expected_edge_bps"),
        "audit_event": latest_audit.get("event"),
        "audit_severity": latest_audit.get("severity"),
        "audit_details": latest_audit.get("details"),
    }


def watch_events_to_csv(events: list[dict]) -> str:
    fields = [
        "at",
        "symbol",
        "feed",
        "auto_submit_enabled",
        "portfolio_source",
        "market_price",
        "market_spread_bps",
        "market_volume_24h",
        "market_volatility_30d",
        "market_timestamp",
        "order_symbol",
        "order_side",
        "order_quantity",
        "order_limit_price",
        "order_expected_edge_bps",
        "audit_event",
        "audit_severity",
        "audit_details",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for event in events:
        writer.writerow(flatten_watch_event(event))
    return output.getvalue()


def summarize_watch_events(events: list[dict]) -> dict[str, object]:
    symbols: dict[str, int] = {}
    feeds: dict[str, int] = {}
    audit_events: dict[str, int] = {}
    audit_details: dict[str, int] = {}
    proposal_count = 0

    for event in events:
        symbol = str(event.get("symbol") or "unknown")
        feed = str(event.get("feed") or "unknown")
        symbols[symbol] = symbols.get(symbol, 0) + 1
        feeds[feed] = feeds.get(feed, 0) + 1

        if event.get("order_proposal") is not None:
            proposal_count += 1

        latest_audit = event.get("latest_audit") if isinstance(event.get("latest_audit"), dict) else {}
        audit_event = str(latest_audit.get("event") or "none")
        audit_detail = str(latest_audit.get("details") or "none")
        audit_events[audit_event] = audit_events.get(audit_event, 0) + 1
        audit_details[audit_detail] = audit_details.get(audit_detail, 0) + 1

    return {
        "total_ticks": len(events),
        "proposal_count": proposal_count,
        "blocked_or_no_proposal_count": len(events) - proposal_count,
        "auto_submit_enabled": False,
        "symbols": symbols,
        "feeds": feeds,
        "audit_events": audit_events,
        "audit_details": audit_details,
        "latest_event": events[-1] if events else None,
    }


def readiness_check(condition: bool, name: str, detail: str = "") -> dict[str, object]:
    return {
        "name": name,
        "status": "PASS" if condition else "FAIL",
        "detail": detail,
    }


def paper_readiness_payload(watch_limit: int = 500) -> dict[str, object]:
    broker = broker_readiness(config.broker)
    watch_events = read_watch_events(watch_limit)
    if not watch_events:
        watch_events = getattr(app.state, "paper_watch_history", [])[-watch_limit:]
    watch_summary = summarize_watch_events(watch_events)

    open_orders: list[object] = []
    open_orders_error = ""
    if broker.status == "ALPACA-PAPER-READY":
        try:
            open_orders = fetch_paper_orders(alpaca_paper_credentials(), status="open", limit=20)
        except (RuntimeError, ValueError) as exc:
            open_orders_error = str(exc)

    checks = [
        readiness_check(config.policy.require_manual_approval is True, "manual_approval_required"),
        readiness_check(config.policy.autonomous_execution is False, "autonomous_execution_disabled"),
        readiness_check(config.policy.kill_switch is False, "kill_switch_not_active"),
        readiness_check(broker.provider == "alpaca", "broker_provider_alpaca"),
        readiness_check(broker.mode == "paper", "broker_mode_paper"),
        readiness_check(broker.live_enabled is False, "live_routing_disabled"),
        readiness_check(broker.status == "ALPACA-PAPER-READY", "broker_paper_ready", broker.reason),
        readiness_check(open_orders_error == "", "paper_orders_query_ok", open_orders_error),
        readiness_check(len(open_orders) == 0 and open_orders_error == "", "no_open_paper_orders", str(open_orders)),
        readiness_check(watch_summary.get("auto_submit_enabled") is False, "watch_auto_submit_disabled"),
        readiness_check(int(watch_summary.get("total_ticks", 0)) >= 1, "watch_history_has_evidence"),
    ]
    passed = all(item["status"] == "PASS" for item in checks)
    return {
        "status": "PAPER-GO" if passed else "PAPER-NO-GO",
        "checks": checks,
        "watch_summary": watch_summary,
    }


def run_paper_strategy_preview(
    *,
    symbol: str,
    feed: str | None,
    cash: float,
    equity: float,
    peak_equity: float,
    daily_pnl: float,
    consecutive_losses: int,
    use_paper_account: bool,
):
    market = fetch_stock_snapshot(
        alpaca_market_data_credentials(feed),
        symbol=symbol,
        default_volatility_30d=float(os.getenv("AI_DEFAULT_VOLATILITY_30D", "0.03")),
    )

    account = None
    if use_paper_account:
        account = fetch_paper_account(alpaca_paper_credentials())
        portfolio = portfolio_from_account(account, consecutive_losses=consecutive_losses)
    else:
        portfolio = PortfolioState(
            cash=cash,
            equity=equity,
            peak_equity=peak_equity,
            daily_pnl=daily_pnl,
            consecutive_losses=consecutive_losses,
            positions={},
        )

    order = system.process_tick(market, portfolio)
    return {
        "mode": "paper_preview_only",
        "auto_submit_enabled": False,
        "manual_confirmation_required": "SUBMIT_PAPER_ORDER",
        "market": serialize_market(market),
        "portfolio_source": "alpaca_paper_account" if account else "request",
        "account": None if account is None else serialize_account(account),
        "order_proposal": serialize_order(order),
        "latest_audit": latest_audit_payload(),
    }


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.post("/simulate_tick")
@limiter.limit("20/minute")
def simulate_tick(request: Request, req: TickRequest, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)

    market = MarketSnapshot(
        symbol=req.symbol,
        price=req.price,
        spread_bps=req.spread_bps,
        volume_24h=req.volume_24h,
        volatility_30d=req.volatility_30d,
        timestamp=datetime.now(timezone.utc),
    )

    portfolio = PortfolioState(
        cash=req.cash,
        equity=req.equity,
        peak_equity=req.peak_equity,
        daily_pnl=req.daily_pnl,
        consecutive_losses=req.consecutive_losses,
        positions={},
    )

    order = system.process_tick(market, portfolio)

    return {
        "order_proposal": serialize_order(order),
        "latest_audit": latest_audit_payload(),
    }


@app.get("/dashboard/summary")
def dashboard_summary(x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    latest_audit = system.audit_log[-1] if system.audit_log else None
    broker = broker_readiness(config.broker)
    return {
        "status": "ok",
        "manual_approval_required": config.policy.require_manual_approval,
        "autonomous_execution": config.policy.autonomous_execution,
        "kill_switch": config.policy.kill_switch,
        "broker": {
            "provider": broker.provider,
            "mode": broker.mode,
            "live_enabled": broker.live_enabled,
            "ready": broker.ready,
            "status": broker.status,
            "reason": broker.reason,
            "market_data_base_url": config.broker.market_data_base_url,
            "market_data_feed": config.broker.market_data_feed,
        },
        "latest_audit": None if not latest_audit else {
            "at": latest_audit.at.isoformat(),
            "event": latest_audit.event,
            "severity": latest_audit.severity,
            "details": latest_audit.details,
        },
    }


@app.get("/broker/paper/market_snapshot")
@limiter.limit("20/minute")
def broker_paper_market_snapshot(
    request: Request,
    symbol: str = "QQQ",
    feed: str | None = None,
    x_api_key: str | None = Header(default=None),
):
    require_api_key(x_api_key)
    broker = broker_readiness(config.broker)
    if broker.status != "ALPACA-PAPER-READY":
        raise HTTPException(status_code=403, detail=broker.status)
    try:
        market = fetch_stock_snapshot(
            alpaca_market_data_credentials(feed),
            symbol=symbol,
            default_volatility_30d=float(os.getenv("AI_DEFAULT_VOLATILITY_30D", "0.03")),
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "source": "alpaca_market_data",
        "feed": feed or config.broker.market_data_feed,
        "snapshot": serialize_market(market),
    }


@app.get("/broker/paper/account")
@limiter.limit("20/minute")
def broker_paper_account(request: Request, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    broker = broker_readiness(config.broker)
    if broker.status != "ALPACA-PAPER-READY":
        raise HTTPException(status_code=403, detail=broker.status)
    try:
        account = fetch_paper_account(alpaca_paper_credentials())
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "source": "alpaca_paper_account",
        "mode": "read_only",
        "account": serialize_account(account),
    }


@app.get("/broker/paper/strategy_preview")
@limiter.limit("20/minute")
def broker_paper_strategy_preview(
    request: Request,
    symbol: str = "QQQ",
    feed: str | None = None,
    cash: float = 1_000.0,
    equity: float = 1_000.0,
    peak_equity: float = 1_000.0,
    daily_pnl: float = 0.0,
    consecutive_losses: int = 0,
    use_paper_account: bool = False,
    x_api_key: str | None = Header(default=None),
):
    require_api_key(x_api_key)
    broker = broker_readiness(config.broker)
    if broker.status != "ALPACA-PAPER-READY":
        raise HTTPException(status_code=403, detail=broker.status)
    try:
        return run_paper_strategy_preview(
            symbol=symbol,
            feed=feed,
            cash=cash,
            equity=equity,
            peak_equity=peak_equity,
            daily_pnl=daily_pnl,
            consecutive_losses=consecutive_losses,
            use_paper_account=use_paper_account,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/broker/status")
def broker_status(x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    broker = broker_readiness(config.broker)
    return {
        "provider": broker.provider,
        "mode": broker.mode,
        "live_enabled": broker.live_enabled,
        "ready": broker.ready,
        "status": broker.status,
        "reason": broker.reason,
    }


@app.post("/broker/paper/order_preview")
def broker_paper_order_preview(req: PaperOrderPreviewRequest, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    broker = broker_readiness(config.broker)
    if broker.live_enabled:
        raise HTTPException(status_code=403, detail="live_broker_routing_disabled_for_current_stage")
    if config.broker.mode != "paper":
        raise HTTPException(status_code=403, detail="broker_mode_must_be_paper")

    order = OrderProposal(
        symbol=req.symbol,
        side=req.side,
        quantity=req.quantity,
        limit_price=req.limit_price,
        expected_edge_bps=req.expected_edge_bps,
        reason=req.reason,
    )
    return {
        "submit_enabled": False,
        "broker_status": broker.status,
        "payload": alpaca_order_payload(order),
    }


@app.post("/broker/paper/submit_order")
@limiter.limit("5/minute")
def broker_paper_submit_order(
    request: Request,
    req: PaperOrderSubmitRequest,
    x_api_key: str | None = Header(default=None),
):
    require_api_key(x_api_key)
    if req.confirm != "SUBMIT_PAPER_ORDER":
        raise HTTPException(status_code=400, detail="confirmation_phrase_required")

    broker = broker_readiness(config.broker)
    if broker.live_enabled:
        raise HTTPException(status_code=403, detail="live_broker_routing_disabled_for_current_stage")
    if broker.status != "ALPACA-PAPER-READY":
        raise HTTPException(status_code=403, detail=broker.status)

    order = OrderProposal(
        symbol=req.symbol,
        side=req.side,
        quantity=req.quantity,
        limit_price=req.limit_price,
        expected_edge_bps=req.expected_edge_bps,
        reason=req.reason,
    )
    try:
        result = submit_paper_order(alpaca_paper_credentials(), order)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    system._audit("paper_order_submitted", "WARN", f"{result.side} {result.symbol} status={result.status}")
    return {
        "submitted": True,
        "broker_order_id": result.broker_order_id,
        "client_order_id": result.client_order_id,
        "status": result.status,
        "symbol": result.symbol,
        "side": result.side,
        "submitted_at": result.submitted_at,
    }


@app.get("/broker/paper/orders")
@limiter.limit("20/minute")
def broker_paper_orders(
    request: Request,
    status: str = "all",
    limit: int = 20,
    x_api_key: str | None = Header(default=None),
):
    require_api_key(x_api_key)
    broker = broker_readiness(config.broker)
    if broker.status != "ALPACA-PAPER-READY":
        raise HTTPException(status_code=403, detail=broker.status)
    try:
        orders = fetch_paper_orders(alpaca_paper_credentials(), status=status, limit=limit)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [
        {
            "broker_order_id": order.broker_order_id,
            "client_order_id": order.client_order_id,
            "status": order.status,
            "symbol": order.symbol,
            "side": order.side,
            "submitted_at": order.submitted_at,
        }
        for order in orders
    ]


@app.get("/broker/paper/readiness")
@limiter.limit("20/minute")
def broker_paper_readiness(
    request: Request,
    watch_limit: int = 500,
    x_api_key: str | None = Header(default=None),
):
    require_api_key(x_api_key)
    if watch_limit <= 0 or watch_limit > 5_000:
        raise HTTPException(status_code=400, detail="watch_limit_must_be_between_1_and_5000")
    return paper_readiness_payload(watch_limit=watch_limit)


@app.post("/broker/paper/cancel_orders")
@limiter.limit("5/minute")
def broker_paper_cancel_orders(
    request: Request,
    req: PaperCancelRequest,
    x_api_key: str | None = Header(default=None),
):
    require_api_key(x_api_key)
    if req.confirm != "CANCEL_PAPER_ORDERS":
        raise HTTPException(status_code=400, detail="confirmation_phrase_required")

    broker = broker_readiness(config.broker)
    if broker.status != "ALPACA-PAPER-READY":
        raise HTTPException(status_code=403, detail=broker.status)

    try:
        cancelled = cancel_paper_orders(alpaca_paper_credentials())
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    system._audit("paper_orders_cancel_requested", "WARN", f"cancelled={len(cancelled)}")
    return {
        "cancel_requested": True,
        "orders": [
            {
                "broker_order_id": order.broker_order_id,
                "client_order_id": order.client_order_id,
                "status": order.status,
                "symbol": order.symbol,
                "side": order.side,
                "submitted_at": order.submitted_at,
            }
            for order in cancelled
        ],
    }


@app.get("/audit")
@limiter.limit("30/minute")
def audit(request: Request, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    return [
        {
            "at": e.at.isoformat(),
            "event": e.event,
            "severity": e.severity,
            "details": e.details,
        }
        for e in system.audit_log[-200:]
    ]


@app.post("/broker/paper/watch_tick")
@limiter.limit("20/minute")
def broker_paper_watch_tick(
    request: Request,
    req: PaperWatchTickRequest,
    x_api_key: str | None = Header(default=None),
):
    require_api_key(x_api_key)
    broker = broker_readiness(config.broker)
    if broker.status != "ALPACA-PAPER-READY":
        raise HTTPException(status_code=403, detail=broker.status)
    try:
        preview = run_paper_strategy_preview(
            symbol=req.symbol,
            feed=req.feed,
            cash=req.cash,
            equity=req.equity,
            peak_equity=req.peak_equity,
            daily_pnl=req.daily_pnl,
            consecutive_losses=req.consecutive_losses,
            use_paper_account=req.use_paper_account,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    event = {
        "at": datetime.now(timezone.utc).isoformat(),
        "symbol": req.symbol.upper(),
        "feed": req.feed or config.broker.market_data_feed,
        "auto_submit_enabled": False,
        "portfolio_source": preview["portfolio_source"],
        "market": preview["market"],
        "order_proposal": preview["order_proposal"],
        "latest_audit": preview["latest_audit"],
    }
    history = getattr(app.state, "paper_watch_history", [])
    history.append(event)
    app.state.paper_watch_history = history[-200:]
    try:
        append_watch_event(event)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"watch_history_write_failed:{exc}") from exc
    return event


@app.get("/broker/paper/watch_history")
@limiter.limit("30/minute")
def broker_paper_watch_history(
    request: Request,
    limit: int = 20,
    x_api_key: str | None = Header(default=None),
):
    require_api_key(x_api_key)
    if limit <= 0 or limit > 200:
        raise HTTPException(status_code=400, detail="limit_must_be_between_1_and_200")
    disk_history = read_watch_events(limit)
    if disk_history:
        return disk_history
    history = getattr(app.state, "paper_watch_history", [])
    return history[-limit:]


@app.get("/broker/paper/watch_summary")
@limiter.limit("30/minute")
def broker_paper_watch_summary(
    request: Request,
    limit: int = 200,
    x_api_key: str | None = Header(default=None),
):
    require_api_key(x_api_key)
    if limit <= 0 or limit > 5_000:
        raise HTTPException(status_code=400, detail="limit_must_be_between_1_and_5000")
    events = read_watch_events(limit)
    if not events:
        events = getattr(app.state, "paper_watch_history", [])[-limit:]
    return summarize_watch_events(events)


@app.get("/broker/paper/watch_export")
@limiter.limit("10/minute")
def broker_paper_watch_export(
    request: Request,
    limit: int = 200,
    format: str = "csv",
    x_api_key: str | None = Header(default=None),
):
    require_api_key(x_api_key)
    if limit <= 0 or limit > 5_000:
        raise HTTPException(status_code=400, detail="limit_must_be_between_1_and_5000")
    events = read_watch_events(limit)
    if format == "jsonl":
        body = "\n".join(json.dumps(event, separators=(",", ":")) for event in events)
        if body:
            body += "\n"
        return Response(
            content=body,
            media_type="application/x-ndjson",
            headers={"Content-Disposition": "attachment; filename=paper_watch_history.jsonl"},
        )
    if format == "csv":
        return Response(
            content=watch_events_to_csv(events),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=paper_watch_history.csv"},
        )
    raise HTTPException(status_code=400, detail="format_must_be_csv_or_jsonl")
