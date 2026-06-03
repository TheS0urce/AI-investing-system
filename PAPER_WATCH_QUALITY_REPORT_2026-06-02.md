# Paper Watch Quality Report - 2026-06-02

## Scope

This report diagnoses read-only paper watch history. It does not submit orders or enable live routing.

## Totals

- Generated at: `2026-06-02T20:11:04.754813+00:00`
- Since: `2026-06-02T13:30:45.554280+00:00`
- Total events: `30`
- Evaluated events: `30`
- Proposal count: `0`
- Auto submit enabled: `False`
- Live trading approved: `False`

## Market Data

- Min volume threshold: `100000.0`
- First liquidity pass: `2026-06-02T13:30:45.554280+00:00`
- First liquidity block: `2026-06-02T13:31:48.816089+00:00`
- Volume min / max: `5246.0` / `581718.0`
- Max spread bps: `19.83042959185775`

## Audit Details

- insufficient_liquidity: `29`
- insufficient_net_edge_after_costs: `1`

## Operator Conclusion

Paper watch ran without proposals. Liquidity was intermittent or still accumulating during the open-window sample; ticks that passed market gates were blocked by net edge after costs.
