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
