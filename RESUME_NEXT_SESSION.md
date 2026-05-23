# Resume Next Session

Trigger phrase: **Let's continue**

## Current State

- Mac API service: running via LaunchAgent `com.aiinvesting.api`
- API URL: `http://127.0.0.1:8001`
- Dashboard apps: `~/Applications/AI Investment`
- Broker: Alpaca paper
- Broker readiness: `ALPACA-PAPER-READY`
- Market data: Alpaca stock snapshots via `https://data.alpaca.markets`, default feed `iex`
- Live routing: `false`
- Autonomous execution: `false`
- Manual approval required: `true`
- Open paper orders: `[]`
- Final validation: `./scripts/check.sh` passed with 54 tests

## Completed Today

- Mac-only deployment and launcher apps
- Alpaca paper credentials configured locally
- Read-only paper account check
- Paper order preview
- Guarded manual paper submit
- Paper order reconciliation
- Guarded paper order cancellation
- Paper order cancellation verified, no open paper orders remain
- Read-only Alpaca market-data snapshot adapter
- Real-time paper strategy preview endpoint
- Read-only paper account endpoint
- Strategy preview can size from read-only paper account state
- Dashboard real-time paper preview controls
- Paper watch-mode tick and in-memory watch history
- Durable paper watch history in `logs/paper_watch_history.jsonl`
- Watch history summary endpoint and dashboard control
- Watch history CSV/JSONL export
- Paper readiness report script returns `PAPER-GO` for paper/watch stage
- Paper readiness API endpoint and dashboard control return `PAPER-GO`
- Guarded paper order drill helper returns `PAPER-DRILL-READY-NO-SUBMIT` by default
- Dry-run paper order drill API endpoint and dashboard control return `PAPER-DRILL-READY-NO-SUBMIT`
- Consolidated paper ops snapshot endpoint and dashboard control return `PAPER-OPS-READY`
- LaunchAgent restarted with paper market-data endpoints live

## Evidence Files

- `OPERATIONS_SNAPSHOT_2026-05-22.md`
- `ALPACA_PAPER_VERIFICATION_2026-05-22.md`
- `PAPER_ORDER_SUBMISSION_2026-05-22.md`
- `PAPER_ORDER_RECONCILIATION_2026-05-22.md`
- `PAPER_ORDER_CANCEL_2026-05-22.md`
- `PAPER_MARKET_DATA_PREVIEW_2026-05-23.md`
- `PAPER_DRY_RUN_DRILL_2026-05-23.md`
- `PAPER_OPS_EVIDENCE_2026-05-23.md`

## First Commands Tomorrow

```bash
cd "/Users/michielburger/Claude Code/AI-investing-system"
git status --short --branch
./scripts/check.sh
.venv/bin/python scripts/check_alpaca_market_data.py
curl -s http://127.0.0.1:8001/dashboard/summary -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/account" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/orders?status=open&limit=20" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/strategy_preview?symbol=QQQ&feed=iex&use_paper_account=true" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
.venv/bin/python scripts/run_paper_watch.py --symbol QQQ --feed iex --interval-seconds 5 --iterations 1
curl -s "http://127.0.0.1:8001/broker/paper/watch_history?limit=5" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/watch_summary?limit=500" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/watch_export?format=csv&limit=5" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
.venv/bin/python scripts/paper_readiness_report.py
.venv/bin/python scripts/paper_daily_ops.py
.venv/bin/python scripts/paper_ops_snapshot.py
.venv/bin/python scripts/paper_ops_evidence.py
curl -s "http://127.0.0.1:8001/broker/paper/readiness?watch_limit=500" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/ops_snapshot?watch_limit=500" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
.venv/bin/python scripts/paper_order_drill.py
curl -s -X POST http://127.0.0.1:8001/broker/paper/order_drill -H "Content-Type: application/json" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)" -d '{"symbol":"QQQ","side":"BUY","quantity":0.001,"limit_price":1.00}'
```

## Next Technical Goal

Continue real-time paper trading, not live trading:

1. Improve strategy signal quality before any live trading discussion.
2. Keep paper submit manual-only behind exact confirmation phrase.
3. Run paper submit/reconcile/cancel drill again.
4. Prepare paper-trading GO/NO-GO checklist before any live discussion.
5. Continue strategy-quality improvements only in paper/watch mode.

## Boundaries

- Do not enable live credentials.
- Do not enable live routing.
- Do not enable autonomous broker submission.
- Do not submit paper orders automatically from the strategy pipeline until a separate GO decision.
