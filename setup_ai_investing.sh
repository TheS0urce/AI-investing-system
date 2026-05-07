#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/TheS0urce/AI-investing-system.git"
PROJECT_DIR="/Users/michielburger/Claude Code/AI-investing-system"

echo "==> Creating project folder"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

echo "==> Initializing git repo"
if [ ! -d .git ]; then
  git init
fi

echo "==> Writing project files"
mkdir -p src/ai_investing examples

cat > .gitignore <<'EOT'
__pycache__/
*.pyc
EOT

cat > README.md <<'EOT'
# AI Investing System (Safety-First)

This repository contains a **self-built AI investing system** designed for retail constraints and safety-first operation.
EOT

cat > requirements.txt <<'EOT'
pydantic>=2.7,<3
EOT

cat > src/ai_investing/__init__.py <<'EOT'
"""Safety-first AI investing system."""
EOT

cat > src/ai_investing/models.py <<'EOT'
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
    conviction: float
    model_confidence: float
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
EOT

cat > src/ai_investing/config.py <<'EOT'
from pydantic import BaseModel, Field

class RiskConfig(BaseModel):
    max_order_notional: float = Field(default=2000.0, gt=0)
    max_symbol_exposure_pct: float = Field(default=0.20, gt=0, le=1)
    max_gross_exposure_pct: float = Field(default=0.90, gt=0, le=1)
    max_drawdown_pct: float = Field(default=0.12, gt=0, le=1)
    max_daily_loss_pct: float = Field(default=0.02, gt=0, le=1)
    max_leverage: float = Field(default=1.0, ge=0)
    max_spread_bps: float = Field(default=30.0, ge=0)
    min_volume_24h: float = Field(default=100000.0, ge=0)
    max_volatility_30d: float = Field(default=0.12, ge=0)
    cooldown_after_losses: int = Field(default=3, ge=0)

class CostConfig(BaseModel):
    fee_bps: float = Field(default=2.0, ge=0)
    slippage_bps: float = Field(default=5.0, ge=0)
    min_net_edge_bps: float = Field(default=2.0)

class PolicyConfig(BaseModel):
    autonomous_execution: bool = False
    require_manual_approval: bool = True
    kill_switch: bool = False

class SystemConfig(BaseModel):
    risk: RiskConfig = RiskConfig()
    costs: CostConfig = CostConfig()
    policy: PolicyConfig = PolicyConfig()
EOT

cat > src/ai_investing/safety.py <<'EOT'
from dataclasses import dataclass
from .config import SystemConfig
from .models import MarketSnapshot, OrderProposal, PortfolioState

@dataclass
class SafetyDecision:
    approved: bool
    reason: str

class SafetyEngine:
    def __init__(self, config: SystemConfig):
        self.config = config

    def review_market(self, market: MarketSnapshot) -> SafetyDecision:
        if market.price <= 0: return SafetyDecision(False, "invalid_price")
        if market.spread_bps > self.config.risk.max_spread_bps: return SafetyDecision(False, "spread_too_wide")
        if market.volume_24h < self.config.risk.min_volume_24h: return SafetyDecision(False, "insufficient_liquidity")
        if market.volatility_30d > self.config.risk.max_volatility_30d: return SafetyDecision(False, "volatility_too_high")
        return SafetyDecision(True, "ok")

    def review_order(self, order: OrderProposal, portfolio: PortfolioState, gross_exposure_notional: float) -> SafetyDecision:
        if self.config.policy.kill_switch: return SafetyDecision(False, "kill_switch_active")
        if portfolio.consecutive_losses >= self.config.risk.cooldown_after_losses: return SafetyDecision(False, "cooldown_active")
        return SafetyDecision(True, "ok")

    def net_edge_check(self, expected_edge_bps: float) -> SafetyDecision:
        costs = self.config.costs.fee_bps + self.config.costs.slippage_bps
        return SafetyDecision(expected_edge_bps - costs >= self.config.costs.min_net_edge_bps, "ok" if expected_edge_bps - costs >= self.config.costs.min_net_edge_bps else "insufficient_net_edge_after_costs")
EOT

cat > src/ai_investing/strategy.py <<'EOT'
from .models import MarketSnapshot, Signal

class Strategy:
    def generate_signal(self, market: MarketSnapshot) -> Signal | None:
        raise NotImplementedError

class SimpleMomentumStrategy(Strategy):
    def generate_signal(self, market: MarketSnapshot) -> Signal | None:
        conviction = min(1.0, max(-1.0, (0.06 - market.volatility_30d) * 12))
        if abs(conviction) < 0.1:
            return None
        return Signal(symbol=market.symbol, conviction=conviction, model_confidence=0.7, rationale="vol-adjusted proxy")
EOT

cat > src/ai_investing/execution.py <<'EOT'
from .models import OrderProposal, PortfolioState, Side, Signal

class ExecutionPlanner:
    def signal_to_order(self, signal: Signal, price: float, portfolio: PortfolioState) -> OrderProposal | None:
        qty = max(0.0, (portfolio.equity * 0.02) * abs(signal.conviction) / max(price, 1e-9))
        if qty == 0:
            return None
        return OrderProposal(
            symbol=signal.symbol,
            side=Side.BUY if signal.conviction > 0 else Side.SELL,
            quantity=qty,
            limit_price=price,
            expected_edge_bps=12 * abs(signal.conviction),
            reason=signal.rationale,
        )
EOT

cat > src/ai_investing/system.py <<'EOT'
from datetime import datetime
from .config import SystemConfig
from .execution import ExecutionPlanner
from .models import AuditEvent, MarketSnapshot, OrderProposal, PortfolioState
from .safety import SafetyEngine
from .strategy import Strategy

class InvestingSystem:
    def __init__(self, config: SystemConfig, strategy: Strategy):
        self.config = config
        self.strategy = strategy
        self.safety = SafetyEngine(config)
        self.execution = ExecutionPlanner()
        self.audit_log: list[AuditEvent] = []

    def _audit(self, event: str, severity: str, details: str) -> None:
        self.audit_log.append(AuditEvent(datetime.utcnow(), event, severity, details))

    def process_tick(self, market: MarketSnapshot, portfolio: PortfolioState) -> OrderProposal | None:
        if not self.safety.review_market(market).approved:
            self._audit("market_block", "WARN", "market checks failed")
            return None
        signal = self.strategy.generate_signal(market)
        if not signal:
            self._audit("no_signal", "INFO", "strategy returned no signal")
            return None
        order = self.execution.signal_to_order(signal, market.price, portfolio)
        if not order:
            self._audit("order_not_created", "INFO", "execution returned none")
            return None
        self._audit("manual_review_required", "INFO", f"proposed {order.side} {order.symbol}")
        return order
EOT

cat > examples/run_demo.py <<'EOT'
from datetime import datetime
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.ai_investing.config import SystemConfig
from src.ai_investing.models import MarketSnapshot, PortfolioState
from src.ai_investing.strategy import SimpleMomentumStrategy
from src.ai_investing.system import InvestingSystem

config = SystemConfig()
strategy = SimpleMomentumStrategy()
system = InvestingSystem(config, strategy)

portfolio = PortfolioState(cash=1000.0, equity=1000.0, peak_equity=1050.0, daily_pnl=-5.0, consecutive_losses=1, positions={"SPY": 1.0})
market = MarketSnapshot(symbol="QQQ", price=430.0, spread_bps=8.0, volume_24h=5000000, volatility_30d=0.03, timestamp=datetime.utcnow())

order = system.process_tick(market, portfolio)
print("Order proposal:", order)
print("Audit log:")
for evt in system.audit_log:
    print(f"- {evt.at.isoformat()} [{evt.severity}] {evt.event}: {evt.details}")
EOT

echo "==> Installing dependencies"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "==> Running demo"
python examples/run_demo.py

echo "==> Commit and push"
git add .
git commit -m "Add safety-first AI investing system scaffold" || true
git remote remove origin >/dev/null 2>&1 || true
git remote add origin "$REPO_URL"
git branch -M main
git push -u origin main

echo "✅ Completed."
