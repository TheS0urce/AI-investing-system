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

from src.ai_investing.config import SystemConfig
from src.ai_investing.models import MarketSnapshot, PortfolioState
from src.ai_investing.strategy import SimpleMomentumStrategy
from src.ai_investing.system import InvestingSystem

load_dotenv()

API_KEY = os.getenv("AI_API_KEY", "")
DEFAULT_RATE = os.getenv("AI_RATE_LIMIT_PER_MINUTE", "60")

if not API_KEY:
    raise RuntimeError("AI_API_KEY missing. Set it in .env")

app = FastAPI(title="AI Investing System", version="0.2.0-secure")

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{DEFAULT_RATE}/minute"])
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})


config = SystemConfig()
strategy = SimpleMomentumStrategy()
system = InvestingSystem(config=config, strategy=strategy)


class TickRequest(BaseModel):
    symbol: str = "QQQ"
    price: float = Field(default=430.0, gt=0)
    spread_bps: float = Field(default=8.0, ge=0)
    volume_24h: float = Field(default=5_000_000, ge=0)
    volatility_30d: float = Field(default=0.03, ge=0)

    cash: float = 1_000.0
    equity: float = 1_000.0
    peak_equity: float = 1_050.0
    daily_pnl: float = -5.0
    consecutive_losses: int = 1


def require_api_key(x_api_key: str | None):
    if x_api_key != API_KEY:
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
@app.get("/dashboard/summary")
def dashboard_summary(x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "service": {"status": "ok", "uptime_seconds": 0, "version": "0.3.0"},
        "security": {
            "api_auth_enforced": True,
            "rate_limit_per_minute": int(DEFAULT_RATE),
            "api_key_age_days": None,
            "tailscale_connected": None,
        },
        "risk": {
            "equity": 1000.0,
            "daily_realized_pnl": 0.0,
            "rolling_30d_drawdown_pct": 0.0,
            "kill_switch_active": config.policy.kill_switch,
        },
        "alerts": {"critical_open": 0, "warning_open": 0},
    }


@app.get("/dashboard/risk")
def dashboard_risk(x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "limits": {
            "max_position_size_pct": 0.05,
            "max_daily_loss_pct": config.risk.max_daily_loss_pct,
            "max_window_drawdown_pct": config.risk.max_drawdown_pct,
        },
        "current": {
            "gross_exposure_pct": 0.0,
            "largest_position_pct": 0.0,
            "daily_realized_loss_pct": 0.0,
            "window_drawdown_pct": 0.0,
        },
        "breaches_30d": {"daily_loss": 0, "window_drawdown": 0, "position_cap": 0},
        "blocked_order_reasons_7d": {},
    }


@app.get("/dashboard/scaling-window")
def dashboard_scaling_window(x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    return {
        "window": {"start": None, "end": None, "days": 30},
        "inputs": {
            "starting_capital": 50,
            "starting_equity_of_window": None,
            "equity": None,
            "realised_profit_after_fees": None,
            "profit_margin": None,
            "ops_ok": True,
            "window_drawdown_pct": 0.0,
        },
        "policy": {
            "reserve_ratio_min": 0.30,
            "max_strategy_allocation_pct": 0.70,
            "max_external_addition_per_review": 50,
        },
        "decision": {
            "allow_new_external_capital": 0.0,
            "reinvest_fraction_of_profit": 0.0,
            "profit_to_reinvest": 0.0,
            "profit_to_reserve": 0.0,
            "strategy_capital_target": 0.0,
            "pause_strategy": False,
            "reason": "placeholder",
        },
    }


@app.get("/dashboard/governance")
def dashboard_governance(x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    return {
        "weekly": {
            "period_start": None,
            "period_end": None,
            "completed_items": 0,
            "total_items": 0,
            "overdue_items": [],
        },
        "monthly": {
            "period": None,
            "completed_items": 0,
            "total_items": 0,
            "signed_off": False,
            "owner": None,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        },
    }


@app.get("/dashboard/audit")
def dashboard_audit(x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    return {
        "count": len(system.audit_log[-200:]),
        "events": [
            {
                "at": e.at.isoformat(),
                "severity": e.severity,
                "event": e.event,
                "details": e.details,
            }
            for e in system.audit_log[-200:]
        ],
    }