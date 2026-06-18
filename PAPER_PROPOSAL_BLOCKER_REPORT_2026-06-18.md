# Paper Proposal Blocker Report - 2026-06-18

## Scope

This report diagnoses why read-only paper watch ticks did not become proposals. It does not change strategy, risk gates, routing, or broker configuration.

## Guardrails

- Auto submit enabled: `False`
- Live trading approved: `False`

## Totals

- Since: `2026-06-18T13:45:00+00:00`
- Evaluated events: `270`
- Proposal count: `0`
- Liquidity pass count at current gate: `270`

## Edge Gap

- Required edge bps: `9.0`
- Observed expected edge min / max after liquidity pass: `5.04` / `11.265159433398415`
- Edge shortfall min / max: `3.96` / `3.96`

## Audit Details

- insufficient_net_edge_after_costs: `233`
- short_sale_disabled: `10`
- spread_too_wide: `27`

## Operator Conclusion

The latest proposal blocker is strategy edge, not execution plumbing: ticks that pass liquidity still fall below the configured net-edge requirement.
