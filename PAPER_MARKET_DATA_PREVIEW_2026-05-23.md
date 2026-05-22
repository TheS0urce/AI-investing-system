# Paper Market Data Preview

Date: 2026-05-23 local / 2026-05-22 UTC

## Status

- Alpaca paper broker readiness: `ALPACA-PAPER-READY`
- Market data base URL: `https://data.alpaca.markets`
- Default feed: `iex`
- Live routing: `false`
- Autonomous execution: `false`
- Paper submit: manual-only with `SUBMIT_PAPER_ORDER`

## Validation

```bash
./scripts/check.sh
```

Result: PASS, 37 tests.

```bash
.venv/bin/python scripts/check_alpaca_market_data.py
```

Result: `ALPACA-MARKET-DATA-OK`.

Latest smoke snapshot:

```json
{
  "status": "ALPACA-MARKET-DATA-OK",
  "symbol": "QQQ",
  "price": 717.25,
  "spread_bps": 1.2555190525020656,
  "volume_24h": 483140.0,
  "volatility_30d": 0.03,
  "timestamp": "2026-05-22T20:23:28.551020+00:00"
}
```

## API Smoke Checks

Market snapshot endpoint:

```bash
curl -s "http://127.0.0.1:8001/broker/paper/market_snapshot?symbol=QQQ&feed=iex" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

Result: returned a read-only QQQ market snapshot.

Strategy preview endpoint:

```bash
curl -s "http://127.0.0.1:8001/broker/paper/strategy_preview?symbol=QQQ&feed=iex&cash=100&equity=100&peak_equity=100&daily_pnl=0&consecutive_losses=0" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

Result: `mode=paper_preview_only`, `auto_submit_enabled=false`, `order_proposal=null`, latest audit `insufficient_net_edge_after_costs`.

## Safety Notes

- No live credentials were added.
- No live broker URL is allowed by the paper order guard.
- The market data adapter is read-only.
- The strategy preview endpoint does not call the paper submit adapter.
