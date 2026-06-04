# Paper Watch Quality Report - 2026-06-03

## Scope

This report diagnoses read-only paper watch history. It does not submit orders or enable live routing.

## Totals

- Generated at: `2026-06-03T20:11:21.554068+00:00`
- Since: `2026-06-03T13:30:40.021861+00:00`
- Total events: `30`
- Evaluated events: `30`
- Proposal count: `0`
- Auto submit enabled: `False`
- Live trading approved: `False`

## Market Data

- Min volume threshold: `100000.0`
- First liquidity pass: `2026-06-03T13:30:40.021861+00:00`
- First liquidity block: `2026-06-03T13:31:43.386831+00:00`
- Volume min / max: `6466.0` / `586617.0`
- Max spread bps: `11.087437132228253`

## Audit Details

- insufficient_liquidity: `21`
- insufficient_net_edge_after_costs: `9`

## Operator Conclusion

Paper watch ran without proposals. Liquidity was intermittent or still accumulating during the open-window sample; ticks that passed market gates were blocked by net edge after costs.
