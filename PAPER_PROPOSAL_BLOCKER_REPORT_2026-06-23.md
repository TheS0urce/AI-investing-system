# Paper Proposal Blocker Report - 2026-06-23

## Scope

This report diagnoses why read-only paper watch ticks did not become proposals. It does not change strategy, risk gates, routing, or broker configuration.

## Guardrails

- Auto submit enabled: `False`
- Live trading approved: `False`

## Totals

- Since: `2026-06-22T13:45:00+00:00`
- Evaluated events: `270`
- Proposal count: `98`
- Liquidity pass count at current gate: `170`

## Edge Gap

- Required edge bps: `9.0`
- Observed expected edge min / max after liquidity pass: `5.04` / `14.0`
- Edge shortfall min / max: `0.031621` / `3.96`

## Audit Details

- insufficient_liquidity: `91`
- insufficient_net_edge_after_costs: `41`
- proposed Side.BUY 0.0038 MSFT: `2`
- proposed Side.BUY 0.0039 MSFT: `1`
- proposed Side.BUY 0.0040 MSFT: `3`
- proposed Side.BUY 0.0041 MSFT: `3`
- proposed Side.BUY 0.0042 MSFT: `2`
- proposed Side.BUY 0.0043 MSFT: `4`
- proposed Side.BUY 0.0044 MSFT: `7`
- proposed Side.BUY 0.0045 MSFT: `7`
- proposed Side.BUY 0.0046 MSFT: `3`
- proposed Side.BUY 0.0047 MSFT: `3`
- proposed Side.BUY 0.0048 MSFT: `1`
- proposed Side.BUY 0.0049 MSFT: `3`
- proposed Side.BUY 0.0050 MSFT: `4`
- proposed Side.BUY 0.0051 MSFT: `2`
- proposed Side.BUY 0.0052 MSFT: `4`
- proposed Side.BUY 0.0053 MSFT: `13`
- proposed Side.BUY 0.0061 NVDA: `2`
- proposed Side.BUY 0.0062 NVDA: `3`
- proposed Side.BUY 0.0063 NVDA: `3`
- proposed Side.BUY 0.0064 NVDA: `2`
- proposed Side.BUY 0.0065 NVDA: `3`
- proposed Side.BUY 0.0066 NVDA: `1`
- proposed Side.BUY 0.0067 NVDA: `2`
- proposed Side.BUY 0.0068 NVDA: `3`
- proposed Side.BUY 0.0069 NVDA: `3`
- proposed Side.BUY 0.0070 NVDA: `1`
- proposed Side.BUY 0.0071 NVDA: `2`
- proposed Side.BUY 0.0072 NVDA: `1`
- proposed Side.BUY 0.0073 NVDA: `4`
- proposed Side.BUY 0.0074 NVDA: `3`
- proposed Side.BUY 0.0076 NVDA: `1`
- proposed Side.BUY 0.0078 NVDA: `2`
- spread_too_wide: `40`

## Operator Conclusion

Proposal generation is no longer blocked in this sample: read-only watch produced manual-review paper proposals. Remaining blocked ticks should be treated as residual gate diagnostics, not a global proposal blocker.
