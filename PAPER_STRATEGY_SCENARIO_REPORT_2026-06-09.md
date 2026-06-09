# Paper Strategy Scenario Report - 2026-06-09

## Scope

This report exercises synthetic paper-trading strategy paths. It does not call Alpaca and does not submit orders.

## Guardrails

- Status: `PAPER-STRATEGY-SCENARIOS-READY`
- Auto submit enabled: `no`
- Live trading approved: `no`

## Scenarios

| Scenario | Volatility | Order Created | Expected Edge Bps | Audit Event | Audit Details |
| --- | ---: | --- | ---: | --- | --- |
| normal_volatility_blocks_on_edge | 0.03 | no | n/a | order_block | insufficient_net_edge_after_costs |
| intraday_momentum_reaches_manual_review | 0.03 | yes | 10.818182 | manual_review_required | proposed Side.BUY 0.0359 QQQ |
| strong_low_volatility_reaches_manual_review | 0.0001 | yes | 10.0632 | manual_review_required | proposed Side.BUY 0.0334 QQQ |
| high_volatility_blocks_market | 0.13 | no | n/a | market_block | volatility_too_high |

## Operator Conclusion

The strategy has a synthetic path to manual review while preserving paper-only and live-routing guardrails.
