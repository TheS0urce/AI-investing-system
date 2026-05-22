# Paper Market Data Preview

Date: 2026-05-23 local / 2026-05-22 UTC

## Status

- Alpaca paper broker readiness: `ALPACA-PAPER-READY`
- Market data base URL: `https://data.alpaca.markets`
- Default feed: `iex`
- Live routing: `false`
- Autonomous execution: `false`
- Paper submit: manual-only with `SUBMIT_PAPER_ORDER`
- Paper account state: read-only endpoint available for strategy preview sizing

## Validation

```bash
./scripts/check.sh
```

Result: PASS, 37 tests.

```bash
.venv/bin/python scripts/check_alpaca_market_data.py
```

Result: `ALPACA-MARKET-DATA-OK`.

```bash
curl -s "http://127.0.0.1:8001/broker/paper/account" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

Result: returned masked read-only paper account state with `status=ACTIVE`.

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

Account-backed strategy preview:

```bash
curl -s "http://127.0.0.1:8001/broker/paper/strategy_preview?symbol=QQQ&feed=iex&use_paper_account=true" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

Result: `portfolio_source=alpaca_paper_account`, `auto_submit_enabled=false`, latest audit `insufficient_net_edge_after_costs`.

Paper watch tick:

```bash
.venv/bin/python scripts/run_paper_watch.py --symbol QQQ --feed iex --interval-seconds 5 --iterations 1
```

Result: `WATCH-TICK-OK`, `auto_submit_enabled=false`, `order_proposal=null`.

Watch history:

```bash
curl -s "http://127.0.0.1:8001/broker/paper/watch_history?limit=5" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

Result: returned the recorded read-only paper watch tick.

Durable watch history:

```bash
wc -l logs/paper_watch_history.jsonl
```

Result after clean smoke test: `1`.

## Safety Notes

- No live credentials were added.
- No live broker URL is allowed by the paper order guard.
- The market data adapter is read-only.
- The strategy preview endpoint does not call the paper submit adapter.
- Watch mode records previews only and does not call the paper submit adapter.
- Watch history is persisted as local gitignored JSONL runtime data.
