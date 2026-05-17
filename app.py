from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from src.ai_investing.config import SystemConfig
from src.ai_investing.models import MarketSnapshot, PortfolioState
from src.ai_investing.strategy import SimpleMomentumStrategy
from src.ai_investing.system import InvestingSystem

load_dotenv()

app = FastAPI(title="AI Investing System", version="0.2.0")


def _require_api_key(x_api_key: str | None) -> None:
    expected = os.getenv("AI_API_KEY", "")
    if not expected:
        # Service is up, but protected routes are unavailable until key is configured.
        raise HTTPException(status_code=503, detail="api_key_not_configured")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.post("/simulate_tick")
def simulate_tick(req: TickRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _require_api_key(x_api_key)

    system = InvestingSystem(config=SystemConfig(), strategy=SimpleMomentumStrategy())

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
        "order_proposal": None
        if order is None
        else {
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "limit_price": order.limit_price,
            "expected_edge_bps": order.expected_edge_bps,
            "reason": order.reason,
        },
        "latest_audit": None
        if not system.audit_log
        else {
            "at": system.audit_log[-1].at.isoformat(),
            "event": system.audit_log[-1].event,
            "severity": system.audit_log[-1].severity,
            "details": system.audit_log[-1].details,
        },
    }


@app.get("/dashboard/summary")
def dashboard_summary(x_api_key: str | None = Header(default=None)) -> dict:
    _require_api_key(x_api_key)
    return {
        "status": "ok",
        "manual_approval_required": True,
        "autonomous_execution": False,
        "risk_mode": "safety_first",
    }


@app.get("/audit")
def audit(x_api_key: str | None = Header(default=None)) -> list[dict]:
    _require_api_key(x_api_key)
    # Stateless endpoint (new system per request) => no accumulated history by design.
    return []