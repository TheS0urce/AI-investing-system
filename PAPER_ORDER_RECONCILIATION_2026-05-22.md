# Paper Order Reconciliation - 2026-05-22

## Result

Read-only reconciliation confirmed the submitted Alpaca paper order.

Order:
- Broker order ID: `f2dc446b-2e1a-4155-9d03-1349527f7b1e`
- Client order ID: `cda21c41-0c7a-4237-b7ad-b96356746c5e`
- Status: `accepted`
- Symbol: `QQQ`
- Side: `buy`
- Submitted at: `2026-05-22T02:18:51.971891323Z`

## Commands

```bash
.venv/bin/python scripts/list_alpaca_paper_orders.py
curl -s "http://127.0.0.1:8001/broker/paper/orders?status=all&limit=20" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

## Safety Boundary

- This was read-only reconciliation.
- No new order was submitted during reconciliation.
- Live routing remains disabled.
- Strategy pipeline still does not auto-submit broker orders.
