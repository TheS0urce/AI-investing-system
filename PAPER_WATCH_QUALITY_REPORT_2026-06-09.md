# Paper Watch Quality Report - 2026-06-09

## Scope

This report diagnoses read-only paper watch history. It does not submit orders or enable live routing.

## Totals

- Generated at: `2026-06-09T21:42:57.096504+00:00`
- Since: `2026-06-09T13:38:32.353301+00:00`
- Total events: `120`
- Evaluated events: `120`
- Proposal count: `19`
- Auto submit enabled: `False`
- Live trading approved: `False`

## Market Data

- Min volume threshold: `100000.0`
- First liquidity pass: `2026-06-09T13:38:45.461885+00:00`
- First liquidity block: `2026-06-09T13:38:32.353301+00:00`
- Volume min / max: `26451.0` / `541050.0`
- Max spread bps: `512.7347845295957`

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

Paper watch produced manual-review proposals while keeping auto-submit disabled and live routing off. Review residual blocks separately before changing gates.
