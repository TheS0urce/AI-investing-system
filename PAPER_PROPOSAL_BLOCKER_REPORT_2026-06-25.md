# Paper Proposal Blocker Report - 2026-06-25

## Scope

This report diagnoses why read-only paper watch ticks did not become proposals. It does not change strategy, risk gates, routing, or broker configuration.

## Guardrails

- Auto submit enabled: `False`
- Live trading approved: `False`

## Totals

- Since: `2026-06-24T13:45:00+00:00`
- Evaluated events: `270`
- Proposal count: `7`
- Liquidity pass count at current gate: `155`

## Edge Gap

- Required edge bps: `9.0`
- Observed expected edge min / max after liquidity pass: `5.04` / `11.535085681873209`
- Edge shortfall min / max: `3.96` / `3.96`

## Audit Details

- insufficient_liquidity: `104`
- insufficient_net_edge_after_costs: `104`
- proposed Side.BUY 0.0034 MSFT: `2`
- proposed Side.BUY 0.0035 MSFT: `1`
- proposed Side.BUY 0.0037 MSFT: `1`
- proposed Side.BUY 0.0040 MSFT: `1`
- proposed Side.BUY 0.0041 MSFT: `1`
- proposed Side.BUY 0.0044 MSFT: `1`
- spread_too_wide: `55`

## Operator Conclusion

Proposal generation is no longer blocked in this sample: read-only watch produced manual-review paper proposals. Remaining blocked ticks should be treated as residual gate diagnostics, not a global proposal blocker.
