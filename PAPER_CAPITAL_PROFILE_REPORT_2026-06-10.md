# Paper Capital Profile Report - 2026-06-10

## Scope

This report validates read-only proposal sizing against a simulated `$100 USD` portfolio. It does not submit orders or enable live routing.

## Session

- Window: `2026-06-10T13:30:48.131558+00:00` through `2026-06-10T14:05:14.128766+00:00`
- Portfolio source: `request`
- Simulated cash / equity / peak equity: `$100 / $100 / $100`
- Total ticks: `150`
- Symbols: `SPY`, `QQQ`, `AAPL`, `MSFT`, `NVDA`
- Ticks per symbol: `30`

## Proposals

- Total manual-review proposals observed: `28`
- BUY proposals: `23`
- SELL proposals: `5`
- Proposal notional range: `$1.301572` to `$2.00`
- Expected edge range: `9.111003` to `14.0` bps
- Configured required edge: `9.0` bps
- Paper orders submitted: `0`

## Launch-Stage Guard

- Short sales are disabled by default.
- Fractional SELL orders cannot open short positions.
- A SELL can pass only when the portfolio owns enough of the symbol to cover the full quantity.
- The manual paper-submit endpoint rejects SELL requests while short sales are disabled.
- Applied to this sample, the `23` BUY proposals remain eligible for manual review and the `5` naked SELL proposals are blocked.

## Conclusion

The `$100` capital-sizing path is working. Proposal notionals fit the intended starter portfolio and clear Alpaca's documented `$1` fractional-share minimum. Long-only enforcement removes the invalid fractional short-sale path without weakening liquidity, spread, edge, exposure, manual-approval, or routing guardrails.
