from __future__ import annotations

from .models import OrderProposal, PortfolioState, Side, Signal


class ExecutionPlanner:
    def signal_to_order(self, signal: Signal, price: float, portfolio: PortfolioState) -> OrderProposal | None:
        if signal.model_confidence < 0.55:
            return None

        risk_budget = portfolio.equity * 0.02
        quantity = max(0.0, risk_budget * abs(signal.conviction) / max(price, 1e-9))
        if quantity == 0:
            return None

        side = Side.BUY if signal.conviction > 0 else Side.SELL
        expected_edge_bps = 12 * abs(signal.conviction)

        return OrderProposal(
            symbol=signal.symbol,
            side=side,
            quantity=quantity,
            limit_price=price,
            expected_edge_bps=expected_edge_bps,
            reason=signal.rationale,
        )
