# Paper Watch Quality Report - 2026-05-28

## Scope

This report diagnoses read-only paper watch history. It does not submit orders or enable live routing.

## Totals

- Generated at: `2026-05-28T22:12:25.900377+00:00`
- Since: `2026-05-28T13:00:00+00:00`
- Total events: `30`
- Evaluated events: `30`
- Proposal count: `0`
- Auto submit enabled: `False`
- Live trading approved: `False`

## Market Data

- Min volume threshold: `100000.0`
- First liquidity pass: `2026-05-28T13:30:51.764793+00:00`
- First liquidity block: `2026-05-28T13:31:54.822963+00:00`
- Volume min / max: `14120.0` / `848003.0`
- Max spread bps: `16.023336551695245`

## Audit Details

- insufficient_liquidity: `19`
- insufficient_net_edge_after_costs: `11`

## Operator Conclusion

Paper watch ran without proposals. Liquidity was intermittent or still accumulating during the open-window sample; ticks that passed market gates were blocked by net edge after costs.
