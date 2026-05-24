from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ai_investing.config import SystemConfig
from src.ai_investing.models import MarketSnapshot, PortfolioState
from src.ai_investing.strategy import SimpleMomentumStrategy
from src.ai_investing.system import InvestingSystem


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    volatility_30d: float
    order_created: bool
    expected_edge_bps: float | None
    audit_event: str
    audit_details: str


def base_portfolio() -> PortfolioState:
    return PortfolioState(
        cash=1000.0,
        equity=1000.0,
        peak_equity=1000.0,
        daily_pnl=0.0,
        consecutive_losses=0,
        positions={},
    )


def run_scenario(name: str, volatility_30d: float) -> ScenarioResult:
    system = InvestingSystem(SystemConfig(), SimpleMomentumStrategy())
    market = MarketSnapshot(
        symbol="QQQ",
        price=430.0,
        spread_bps=8.0,
        volume_24h=5_000_000,
        volatility_30d=volatility_30d,
        timestamp=datetime.now(timezone.utc),
    )
    order = system.process_tick(market, base_portfolio())
    latest = system.audit_log[-1]
    return ScenarioResult(
        name=name,
        volatility_30d=volatility_30d,
        order_created=order is not None,
        expected_edge_bps=None if order is None else round(order.expected_edge_bps, 6),
        audit_event=latest.event,
        audit_details=latest.details,
    )


def build_scenario_report() -> dict[str, object]:
    scenarios = [
        run_scenario("normal_volatility_blocks_on_edge", 0.03),
        run_scenario("strong_low_volatility_reaches_manual_review", 0.0001),
        run_scenario("high_volatility_blocks_market", 0.13),
    ]
    return {
        "status": "PAPER-STRATEGY-SCENARIOS-READY",
        "auto_submit_enabled": False,
        "live_trading_approved": False,
        "scenarios": [asdict(item) for item in scenarios],
    }


def main() -> int:
    print(json.dumps(build_scenario_report(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
