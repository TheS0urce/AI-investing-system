# Paper Order Submission - 2026-05-22

## Result

- Environment: Alpaca paper
- Live routing enabled: `false`
- Endpoint: `POST /broker/paper/submit_order`
- Confirmation phrase required: `SUBMIT_PAPER_ORDER`
- Submitted: `true`
- Broker order ID: `f2dc446b-2e1a-4155-9d03-1349527f7b1e`
- Client order ID: `cda21c41-0c7a-4237-b7ad-b96356746c5e`
- Status: `accepted`
- Symbol: `QQQ`
- Side: `buy`
- Quantity: `0.01`
- Limit price: `430.00`
- Submitted at: `2026-05-22T02:18:51.971891323Z`

## Guard Evidence

- Submit endpoint requires API authentication.
- Submit endpoint requires exact confirmation phrase.
- Submit endpoint checks broker status is `ALPACA-PAPER-READY`.
- Adapter blocks non-paper Alpaca base URLs.
- Strategy pipeline still does not auto-submit broker orders.
- Live broker routing remains disabled.

## NO-GO Boundary

- This was a paper-only order.
- This does not approve live trading.
- No live broker credentials are configured.
