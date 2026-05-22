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

from src.ai_investing.broker import broker_readiness
from src.ai_investing.config import SystemConfig
from src.ai_investing.models import MarketSnapshot, PortfolioState
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
        "order_proposal": None if order is None else {
            "symbol": order.symbol,
            "side": str(order.side.value),
            "quantity": order.quantity,
            "limit_price": order.limit_price,
            "expected_edge_bps": order.expected_edge_bps,
            "reason": order.reason,
        },
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
        },
        "latest_audit": None if not latest_audit else {
            "at": latest_audit.at.isoformat(),
            "event": latest_audit.event,
            "severity": latest_audit.severity,
            "details": latest_audit.details,
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
