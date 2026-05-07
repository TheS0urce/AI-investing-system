from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    price: float
    spread_bps: float
    volume_24h: float
    volatility_30d: float
    timestamp: datetime


@dataclass(frozen=True)
class Signal:
    symbol: str
    conviction: float  # -1 to +1
    model_confidence: float  # 0 to 1
    rationale: str


@dataclass(frozen=True)
class OrderProposal:
    symbol: str
    side: Side
    quantity: float
    limit_price: float
    expected_edge_bps: float
    reason: str


@dataclass
class PortfolioState:
    cash: float
    equity: float
    peak_equity: float
    daily_pnl: float
    consecutive_losses: int
    positions: dict[str, float] = field(default_factory=dict)


@dataclass
class AuditEvent:
    at: datetime
    event: str
    severity: str
    details: str
