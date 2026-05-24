from src.ai_investing.execution import EXPECTED_EDGE_BPS_PER_CONVICTION, ExecutionPlanner
from src.ai_investing.models import PortfolioState, Signal


def test_execution_uses_improved_edge_model_for_strong_signals():
    planner = ExecutionPlanner()
    portfolio = PortfolioState(
        cash=1000.0,
        equity=1000.0,
        peak_equity=1000.0,
        daily_pnl=0.0,
        consecutive_losses=0,
        positions={},
    )

    order = planner.signal_to_order(
        Signal(
            symbol="QQQ",
            conviction=0.72,
            model_confidence=0.76,
            rationale="test",
        ),
        price=100.0,
        portfolio=portfolio,
    )

    assert order is not None
    assert EXPECTED_EDGE_BPS_PER_CONVICTION == 14.0
    assert order.expected_edge_bps == 10.08
