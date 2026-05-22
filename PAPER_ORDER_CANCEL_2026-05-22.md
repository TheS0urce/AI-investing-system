# Paper Order Cancel - 2026-05-22

## Result

- Environment: Alpaca paper
- Live routing enabled: `false`
- Endpoint: `POST /broker/paper/cancel_orders`
- Confirmation phrase required: `CANCEL_PAPER_ORDERS`
- Cancel requested: `true`
- Cancel response count: `1`
- Post-cancel open orders: `[]`
- Audit event: `paper_orders_cancel_requested`

## Cancelled Paper Order Context

The cancellation request targeted open paper orders. Before cancellation, the open paper order list contained:

- Broker order ID: `f2dc446b-2e1a-4155-9d03-1349527f7b1e`
- Status: `accepted`
- Symbol: `QQQ`
- Side: `buy`

## Safety Boundary

- This affected Alpaca paper orders only.
- Live routing remains disabled.
- Strategy pipeline still does not auto-submit or auto-cancel broker orders.
