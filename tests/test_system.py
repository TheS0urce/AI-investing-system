from datetime import datetime, timezone

from src.ai_investing.config import SystemConfig
from src.ai_investing.models import MarketSnapshot, PortfolioState
from src.ai_investing.strategy import SimpleMomentumStrategy
from src.ai_investing.system import InvestingSystem


def base_market() -> MarketSnapshot:
    return MarketSnapshot(
        symbol="QQQ",
        price=430.0,
        spread_bps=8.0,
        volume_24h=5_000_000,
        volatility_30d=0.03,
        timestamp=datetime.now(timezone.utc),
    )


def base_portfolio() -> PortfolioState:
    return PortfolioState(
        cash=1000.0,
        equity=1000.0,
        peak_equity=1050.0,
        daily_pnl=-5.0,
        consecutive_losses=1,
        positions={"SPY": 1.0},
    )


def test_process_tick_logs_block_when_edge_fails():
    cfg = SystemConfig()
    system = InvestingSystem(cfg, SimpleMomentumStrategy())
    order = system.process_tick(base_market(), base_portfolio())
    assert order is None
    assert len(system.audit_log) >= 1
    assert system.audit_log[-1].event == "order_block"
    assert system.audit_log[-1].details == "insufficient_net_edge_after_costs"


def test_process_tick_blocks_bad_market():
    cfg = SystemConfig()
    system = InvestingSystem(cfg, SimpleMomentumStrategy())
    market = base_market()
    market = MarketSnapshot(
        symbol=market.symbol,
        price=market.price,
        spread_bps=999.0,  # bad spread
        volume_24h=market.volume_24h,
        volatility_30d=market.volatility_30d,
        timestamp=market.timestamp,
    )
    order = system.process_tick(market, base_portfolio())
    assert order is None
    assert system.audit_log[-1].event == "market_block"