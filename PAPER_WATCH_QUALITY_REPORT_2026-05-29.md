# Paper Watch Quality Report - 2026-05-29

## Scope

This report diagnoses read-only paper watch history. It does not submit orders or enable live routing.

## Totals

- Generated at: `2026-05-29T20:10:54.466233+00:00`
- Since: `2026-05-28T14:01:24.910822+00:00`
- Total events: `31`
- Evaluated events: `31`
- Proposal count: `0`
- Auto submit enabled: `False`
- Live trading approved: `False`

## Market Data

- Min volume threshold: `100000.0`
- First liquidity pass: `2026-05-28T14:01:24.910822+00:00`
- First liquidity block: `2026-05-29T13:31:41.207728+00:00`
- Volume min / max: `7499.0` / `712765.0`
- Max spread bps: `15.3148696541956`

## Audit Details

- insufficient_liquidity: `29`
- insufficient_net_edge_after_costs: `2`

## Operator Conclusion

Paper watch ran without proposals. Liquidity was intermittent or still accumulating during the open-window sample; ticks that passed market gates were blocked by net edge after costs.
