# Paper Trading GO/NO-GO Checklist - 2026-05-24

## Hard Guards

- Paper mode only.
- Live routing must remain disabled.
- Autonomous execution must remain disabled.
- Manual approval must remain required.
- Do not submit a paper order unless the operator explicitly approves it.

## Gates

### 1. API is running

- Command: `curl http://127.0.0.1:8001/health`
- GO condition: Response status is ok.

### 2. Broker is paper-ready

- Command: `.venv/bin/python scripts/check_alpaca_paper_account.py`
- GO condition: Status is ALPACA-PAPER-ACCOUNT-OK.

### 3. Live routing is disabled

- Command: `curl http://127.0.0.1:8001/broker/status -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"`
- GO condition: Mode is paper and live_enabled is false.

### 4. Daily ops is green

- Command: `.venv/bin/python scripts/paper_daily_ops.py`
- GO condition: Status is PAPER-DAILY-GO.

### 5. Strategy quality is acceptable

- Command: `.venv/bin/python scripts/strategy_quality_report.py`
- GO condition: Status is STRATEGY-QUALITY-OK.

### 6. Scenario evidence is current

- Command: `.venv/bin/python scripts/paper_strategy_scenarios.py --write-report`
- GO condition: Report confirms no auto-submit and no live trading approval.

### 7. Market session is open

- Command: `.venv/bin/python scripts/paper_market_session_plan.py`
- GO condition: Status is MARKET-OPEN-RUN-WATCH.

### 8. No open paper orders

- Command: `.venv/bin/python scripts/list_alpaca_paper_orders.py --status open --limit 20`
- GO condition: Open order list is empty before starting a watch session.

### 9. Read-only watch evidence captured

- Command: `.venv/bin/python scripts/run_paper_watch.py --symbol QQQ --feed iex --interval-seconds 60 --iterations 30`
- GO condition: Watch completes without auto-submit and writes history.

### 10. Watch report written

- Command: `.venv/bin/python scripts/paper_watch_report.py`
- GO condition: Report shows proposals, blocks, and watch statuses for review.

## Stop Conditions

- Any command returns NO-GO, FAIL, 401, or network errors.
- Any status reports live_enabled as true.
- Any unexpected open order appears before the session.
- The market is closed unless the session is explicitly a closed-market dry run.
