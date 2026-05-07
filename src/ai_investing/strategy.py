from __future__ import annotations

from .models import MarketSnapshot, Signal


class Strategy:
    def generate_signal(self, market: MarketSnapshot) -> Signal | None:
        raise NotImplementedError


class SimpleMomentumStrategy(Strategy):
    """Placeholder model-driven strategy.

    Uses simple volatility-adjusted heuristics to illustrate integration points.
    """

    def generate_signal(self, market: MarketSnapshot) -> Signal | None:
        if market.volatility_30d <= 0:
            return None

        conviction = min(1.0, max(-1.0, (0.06 - market.volatility_30d) * 12))
        if abs(conviction) < 0.1:
            return None

        return Signal(
            symbol=market.symbol,
            conviction=conviction,
            model_confidence=min(0.95, 0.4 + abs(conviction) / 2),
            rationale="volatility-adjusted momentum proxy",
        )
