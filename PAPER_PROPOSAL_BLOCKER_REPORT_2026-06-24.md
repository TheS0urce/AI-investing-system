# Paper Proposal Blocker Report - 2026-06-23

## Scope

This report diagnoses why read-only paper watch ticks did not become proposals. It does not change strategy, risk gates, routing, or broker configuration.

## Guardrails

- Auto submit enabled: `False`
- Live trading approved: `False`

## Totals

- Since: `2026-06-23T13:45:00+00:00`
- Evaluated events: `270`
- Proposal count: `56`
- Liquidity pass count at current gate: `252`

## Edge Gap

- Required edge bps: `9.0`
- Observed expected edge min / max after liquidity pass: `5.04` / `12.950527004618785`
- Edge shortfall min / max: `0.05204` / `3.96`

## Audit Details

- insufficient_liquidity: `18`
- insufficient_net_edge_after_costs: `135`
- proposed Side.BUY 0.0019 QQQ: `3`
- proposed Side.BUY 0.0020 QQQ: `8`
- proposed Side.BUY 0.0021 QQQ: `2`
- proposed Side.BUY 0.0022 QQQ: `12`
- proposed Side.BUY 0.0023 QQQ: `12`
- proposed Side.BUY 0.0024 QQQ: `8`
- proposed Side.BUY 0.0026 QQQ: `1`
- proposed Side.BUY 0.0035 MSFT: `2`
- proposed Side.BUY 0.0039 MSFT: `1`
- proposed Side.BUY 0.0064 NVDA: `2`
- proposed Side.BUY 0.0065 NVDA: `1`
- proposed Side.BUY 0.0066 NVDA: `1`
- proposed Side.BUY 0.0067 NVDA: `2`
- proposed Side.BUY 0.0074 NVDA: `1`
- spread_too_wide: `61`

## Operator Conclusion

Proposal generation is no longer blocked in this sample: read-only watch produced manual-review paper proposals. Remaining blocked ticks should be treated as residual gate diagnostics, not a global proposal blocker.
