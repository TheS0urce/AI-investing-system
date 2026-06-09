from __future__ import annotations

from .models import MarketSnapshot, Signal

MIN_INTRADAY_SIGNAL_BPS = 70.0
INTRADAY_BPS_PER_FULL_CONVICTION = 110.0


class Strategy:
    def generate_signal(self, market: MarketSnapshot) -> Signal | None:
        raise NotImplementedError


def intraday_momentum_conviction(market: MarketSnapshot) -> float | None:
    if abs(market.intraday_change_bps) < MIN_INTRADAY_SIGNAL_BPS:
        return None
    return min(1.0, max(-1.0, market.intraday_change_bps / INTRADAY_BPS_PER_FULL_CONVICTION))


def volatility_proxy_conviction(market: MarketSnapshot) -> float | None:
    if market.volatility_30d <= 0:
        return None
    conviction = min(1.0, max(-1.0, (0.06 - market.volatility_30d) * 12))
    return conviction if abs(conviction) >= 0.1 else None


class SimpleMomentumStrategy(Strategy):
    """Conservative paper momentum strategy.

    Uses observable intraday movement first and falls back to the older
    volatility proxy for synthetic tests and sparse snapshots.
    """

    def generate_signal(self, market: MarketSnapshot) -> Signal | None:
        conviction = intraday_momentum_conviction(market)
        rationale = "intraday momentum from daily open"
        if conviction is None:
            conviction = volatility_proxy_conviction(market)
            rationale = "volatility-adjusted momentum proxy"
        if conviction is None:
            return None

        return Signal(
            symbol=market.symbol,
            conviction=conviction,
            model_confidence=min(0.95, 0.4 + abs(conviction) / 2),
            rationale=rationale,
        )
