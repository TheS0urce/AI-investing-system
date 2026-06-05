# Paper Watch Quality Report - 2026-06-04

## Scope

This report diagnoses read-only paper watch history. It does not submit orders or enable live routing.

## Totals

- Generated at: `2026-06-04T20:10:58.955071+00:00`
- Since: `2026-06-04T13:31:03.780773+00:00`
- Total events: `30`
- Evaluated events: `30`
- Proposal count: `0`
- Auto submit enabled: `False`
- Live trading approved: `False`

## Market Data

- Min volume threshold: `100000.0`
- First liquidity pass: `2026-06-04T13:50:56.095708+00:00`
- First liquidity block: `2026-06-04T13:31:03.780773+00:00`
- Volume min / max: `9815.0` / `142287.0`
- Max spread bps: `11.40452107799921`

## Audit Details

- insufficient_liquidity: `19`
- insufficient_net_edge_after_costs: `11`

## Operator Conclusion

Paper watch ran without proposals. Liquidity was intermittent or still accumulating during the open-window sample; ticks that passed market gates were blocked by net edge after costs.
