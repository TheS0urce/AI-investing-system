# Paper Gate Scenario Report - 2026-06-05

## Scope

This report replays local paper watch history through candidate market gates. It does not change live code paths, submit orders, or enable live routing.

## Guardrails

- Status: `PAPER-GATE-SCENARIOS-READY`
- Auto submit enabled: `False`
- Live trading approved: `False`

## Scenarios

| Min Volume | Evaluated | Proposals | Audit Details |
| ---: | ---: | ---: | --- |
| 100000.0 | 30 | 0 | insufficient_liquidity=19, insufficient_net_edge_after_costs=11 |
| 75000.0 | 30 | 0 | insufficient_liquidity=14, insufficient_net_edge_after_costs=16 |
| 50000.0 | 30 | 0 | insufficient_liquidity=9, insufficient_net_edge_after_costs=21 |
| 25000.0 | 30 | 0 | insufficient_liquidity=4, insufficient_net_edge_after_costs=26 |

## Operator Conclusion

Liquidity thresholds affect which gate blocks first, but replay still produces no proposals because ticks that pass market gates fail net-edge checks.
