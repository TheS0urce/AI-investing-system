from datetime import datetime, timezone

from src.ai_investing.config import SystemConfig
from src.ai_investing.models import MarketSnapshot, OrderProposal, PortfolioState, Side
from src.ai_investing.safety import SafetyEngine


def base_portfolio() -> PortfolioState:
    return PortfolioState(
        cash=1000.0,
        equity=1000.0,
        peak_equity=1000.0,
        daily_pnl=0.0,
        consecutive_losses=0,
        positions={},
    )


def test_market_rejects_wide_spread():
    safety = SafetyEngine(SystemConfig())
    market = MarketSnapshot(
        symbol="QQQ",
        price=400.0,
        spread_bps=999.0,  # too wide
        volume_24h=10_000_000,
        volatility_30d=0.03,
        timestamp=datetime.now(timezone.utc),
    )
    decision = safety.review_market(market)
    assert not decision.approved
    assert decision.reason == "spread_too_wide"


def test_market_rejects_low_liquidity():
    safety = SafetyEngine(SystemConfig())
    market = MarketSnapshot(
        symbol="QQQ",
        price=400.0,
        spread_bps=5.0,
        volume_24h=1.0,  # too low
        volatility_30d=0.03,
        timestamp=datetime.now(timezone.utc),
    )
    decision = safety.review_market(market)
    assert not decision.approved
    assert decision.reason == "insufficient_liquidity"


def test_net_edge_rejects_when_costs_dominate():
    safety = SafetyEngine(SystemConfig())
    decision = safety.net_edge_check(expected_edge_bps=1.0)
    assert not decision.approved
    assert decision.reason == "insufficient_net_edge_after_costs"


def test_order_rejects_when_kill_switch_active():
    cfg = SystemConfig()
    cfg.policy.kill_switch = True
    safety = SafetyEngine(cfg)
    order = OrderProposal(
        symbol="QQQ",
        side=Side.BUY,
        quantity=1.0,
        limit_price=100.0,
        expected_edge_bps=10.0,
        reason="test",
    )
    decision = safety.review_order(order, base_portfolio(), gross_exposure_notional=0.0)
    assert not decision.approved
    assert decision.reason == "kill_switch_active"