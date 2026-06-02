# Paper Gate Scenario Report - 2026-06-02

## Scope

This report replays local paper watch history through candidate market gates. It does not change live code paths, submit orders, or enable live routing.

## Guardrails

- Status: `PAPER-GATE-SCENARIOS-READY`
- Auto submit enabled: `False`
- Live trading approved: `False`

## Scenarios

| Min Volume | Evaluated | Proposals | Audit Details |
| ---: | ---: | ---: | --- |
| 100000.0 | 30 | 0 | insufficient_liquidity=30 |
| 75000.0 | 30 | 0 | insufficient_liquidity=30 |
| 50000.0 | 30 | 0 | insufficient_liquidity=17, insufficient_net_edge_after_costs=13 |
| 25000.0 | 30 | 0 | insufficient_liquidity=6, insufficient_net_edge_after_costs=24 |

## Operator Conclusion

Liquidity thresholds affect which gate blocks first, but replay still produces no proposals because ticks that pass market gates fail net-edge checks.
