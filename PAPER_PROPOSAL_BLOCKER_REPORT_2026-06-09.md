# Paper Proposal Blocker Report - 2026-06-09

## Scope

This report diagnoses why read-only paper watch ticks did not become proposals. It does not change strategy, risk gates, routing, or broker configuration.

## Guardrails

- Auto submit enabled: `False`
- Live trading approved: `False`

## Totals

- Since: `2026-06-09T13:38:32.353301+00:00`
- Evaluated events: `120`
- Proposal count: `19`
- Liquidity pass count at current gate: `91`

## Edge Gap

- Required edge bps: `9.0`
- Observed expected edge min / max after liquidity pass: `5.04` / `14.0`
- Edge shortfall min / max: `3.96` / `3.96`

## Audit Details

- insufficient_liquidity: `25`
- insufficient_net_edge_after_costs: `52`
- order_notional_too_large: `2`
- proposed Side.SELL 4.6980 AAPL: `1`
- proposed Side.SELL 5.4059 AAPL: `1`
- proposed Side.SELL 5.8993 AAPL: `1`
- proposed Side.SELL 6.3318 AAPL: `1`
- proposed Side.SELL 6.3421 AAPL: `1`
- proposed Side.SELL 6.6212 NVDA: `1`
- proposed Side.SELL 6.6420 NVDA: `1`
- proposed Side.SELL 6.7379 AAPL: `1`
- proposed Side.SELL 6.7442 AAPL: `1`
- proposed Side.SELL 6.7513 AAPL: `1`
- proposed Side.SELL 6.7552 AAPL: `1`
- proposed Side.SELL 6.7572 AAPL: `1`
- proposed Side.SELL 6.7861 AAPL: `1`
- proposed Side.SELL 6.7870 AAPL: `1`
- proposed Side.SELL 6.7922 AAPL: `1`
- proposed Side.SELL 7.4326 NVDA: `1`
- proposed Side.SELL 7.9118 NVDA: `1`
- proposed Side.SELL 7.9952 NVDA: `1`
- proposed Side.SELL 8.2872 NVDA: `1`
- spread_too_wide: `22`

## Operator Conclusion

Proposal generation is no longer blocked in this sample: read-only watch produced manual-review paper proposals. Remaining blocked ticks should be treated as residual gate diagnostics, not a global proposal blocker.
