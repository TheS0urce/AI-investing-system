import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from src.ai_investing.alpaca import (
    AlpacaMarketDataCredentials,
    AlpacaPaperCredentials,
    alpaca_order_payload,
    cancel_paper_orders,
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


def alpaca_market_data_credentials(feed: str | None = None) -> AlpacaMarketDataCredentials:
    return AlpacaMarketDataCredentials(
        api_key=os.getenv("ALPACA_PAPER_API_KEY", ""),
        secret_key=os.getenv("ALPACA_PAPER_SECRET_KEY", ""),
        base_url=os.getenv("ALPACA_MARKET_DATA_BASE_URL", "https://data.alpaca.markets"),
        feed=feed or os.getenv("ALPACA_MARKET_DATA_FEED", "iex"),
    )


def require_api_key(x_api_key: str | None):
    expected = os.getenv("AI_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="api_key_not_configured")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="invalid api key")


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
        "latest_audit": None if not system.audit_log else {
            "at": system.audit_log[-1].at.isoformat(),
            "event": system.audit_log[-1].event,
            "severity": system.audit_log[-1].severity,
            "details": system.audit_log[-1].details,
        },
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
        "order_proposal": serialize_order(order),
        "latest_audit": None if not system.audit_log else {
            "at": system.audit_log[-1].at.isoformat(),
            "event": system.audit_log[-1].event,
            "severity": system.audit_log[-1].severity,
            "details": system.audit_log[-1].details,
        },
    }


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

    credentials = AlpacaPaperCredentials(
        api_key=os.getenv("ALPACA_PAPER_API_KEY", ""),
        secret_key=os.getenv("ALPACA_PAPER_SECRET_KEY", ""),
        base_url=os.getenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets"),
    )
    order = OrderProposal(
        symbol=req.symbol,
        side=req.side,
        quantity=req.quantity,
        limit_price=req.limit_price,
        expected_edge_bps=req.expected_edge_bps,
        reason=req.reason,
    )
    try:
        result = submit_paper_order(credentials, order)
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
    credentials = AlpacaPaperCredentials(
        api_key=os.getenv("ALPACA_PAPER_API_KEY", ""),
        secret_key=os.getenv("ALPACA_PAPER_SECRET_KEY", ""),
        base_url=os.getenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets"),
    )
    try:
        orders = fetch_paper_orders(credentials, status=status, limit=limit)
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

    credentials = AlpacaPaperCredentials(
        api_key=os.getenv("ALPACA_PAPER_API_KEY", ""),
        secret_key=os.getenv("ALPACA_PAPER_SECRET_KEY", ""),
        base_url=os.getenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets"),
    )
    try:
        cancelled = cancel_paper_orders(credentials)
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
