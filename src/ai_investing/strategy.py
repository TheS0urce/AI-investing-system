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
