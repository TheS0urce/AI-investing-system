# Resume Next Session

Trigger phrase: **Let's continue**

Operator resume command: **Lets continue.**

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
- Final validation: `./scripts/check.sh` passed with 126 tests

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
- Read-only Alpaca paper clock endpoint returns market open/close state
- Read-only paper session-plan endpoint and dashboard control return `MARKET-CLOSED-WAIT` or `MARKET-OPEN-RUN-WATCH`
- Paper watch mode skips strategy evaluation when the market is closed by default
- Guarded market-open paper watch launcher refuses to run while market is closed
- Paper market-open preflight combines session plan, readiness, strategy quality, and open-order checks
- Paper market-open preflight API endpoint and dashboard control are available
- `AI Investing Market Preflight.app` is installed in `~/Applications/AI Investment`
- Session plan and preflight include operator-local market times, defaulting to `Pacific/Auckland`
- Session plan and preflight include `time_until_next_open` / `time_until_next_close` countdown fields
- Paper next-action helper returns compact `WAIT_FOR_MARKET_OPEN`, `RUN_GUARDED_WATCH`, or `FIX_PREFLIGHT_REASONS` guidance
- Paper next-action API endpoint and dashboard control are available
- `AI Investing Next Action.app` is installed in `~/Applications/AI Investment`
- Paper watch report helper generated `PAPER_WATCH_REPORT_2026-05-23.md`
- Paper market session planner returns `MARKET-CLOSED-WAIT` until next paper market open
- Strategy quality diagnostic returns `STRATEGY-QUALITY-OK` after expected-edge model improvement
- Strategy quality API endpoint and dashboard control return `STRATEGY-QUALITY-OK`
- Synthetic paper strategy scenario API endpoint and dashboard control return `PAPER-STRATEGY-SCENARIOS-READY`
- Paper GO/NO-GO checklist script, API endpoint, and dashboard control are available
- Paper strategy scenario report generated `PAPER_STRATEGY_SCENARIO_REPORT_2026-05-24.md`
- Paper GO/NO-GO checklist generated `PAPER_GO_NO_GO_CHECKLIST_2026-05-24.md`
- Daily Ops includes market clock fields and NO-GO reasons
- Mac launcher verification returns `LAUNCHERS-READY`
- Mac launcher verification expects 7 apps including Market Preflight and Next Action
- LaunchAgent restarted with paper market-data and paper clock endpoints live
- Deterministic scaling policy report helper added for 38% reinvestment / 62% reserve and ROI-tier allocation evidence
- Scaling policy tests added; `src/ai_investing/scaling.py` is directly covered
- Scaling policy report generated `SCALING_POLICY_REPORT_2026-05-25.md`
- Paper next-action currently reports `WAIT_FOR_MARKET_OPEN`; next paper market open is 2026-05-27 01:30 Pacific/Auckland
- Market-open paper watch launcher now requires full `PAPER-MARKET-OPEN-GO` preflight before any watch tick runs
- Closed-market launcher probe returned `PAPER-WATCH-NO-GO` with `market_open_preflight_failed` and `session_plan=MARKET-CLOSED-WAIT`
- Pre-open daily ops generated `PAPER-DAILY-GO` with `PAPER-GO`, live routing disabled, autonomous execution disabled, and open paper orders at 0
- Paper GO/NO-GO checklist refreshed so the watch gate requires full `PAPER-MARKET-OPEN-GO` preflight
- Paper watch report generated `PAPER_WATCH_REPORT_2026-05-25.md`
- Automation `market-open-paper-watch` is ACTIVE for Wednesday 2026-05-27 01:25 Pacific/Auckland; it runs preflight and only runs guarded QQQ/iex paper watch if status is `PAPER-MARKET-OPEN-GO`
- Automation `market-close-paper-summary` is ACTIVE for Wednesday 2026-05-27 08:10 Pacific/Auckland; it generates post-close evidence and a morning seed message
- Automation guardrails: no live routing, no autonomous submission, no paper order confirmation phrase, no broker config changes
- Wednesday 2026-05-27 automation review: market-open watch fired at 01:25 Pacific/Auckland, before the 01:30 open, so it failed closed with `WAIT_FOR_MARKET_OPEN` / `session_plan=MARKET-CLOSED-WAIT`; no fresh watch evidence was added.
- Automations rescheduled for next open window: `market-open-paper-watch` Thursday 2026-05-28 01:35 Pacific/Auckland, `market-close-paper-summary` Thursday 2026-05-28 08:10 Pacific/Auckland.
- Current next action after review: `WAIT_FOR_MARKET_OPEN`; next open is Thursday 2026-05-28 01:30 Pacific/Auckland and next close is Thursday 2026-05-28 08:00 Pacific/Auckland.
- Guarded market-open watch now retries closed-market preflight up to 3 total attempts with 5 minutes between attempts; it only retries `session_plan=MARKET-CLOSED-WAIT`, and still fails closed for readiness, strategy quality, open-order, or other preflight failures.
- Thursday 2026-05-28 automation review: `paper_next_action.py` saw `RUN_GUARDED_WATCH`, but the automation's separate direct `paper_market_open_preflight.py` command hit sandbox network permissions, so no fresh watch evidence was added.
- Persisted approved execution paths for `paper_market_open_preflight.py` and `run_market_open_paper_watch.py`; one-attempt closed-market probes now run and fail closed with local API evidence instead of sandbox network errors.
- Automations rescheduled for next open window: `market-open-paper-watch` Friday 2026-05-29 01:30 Pacific/Auckland, `market-close-paper-summary` Friday 2026-05-29 08:10 Pacific/Auckland.
- Updated watch automation now runs `run_market_open_paper_watch.py` directly; that script performs full preflight and retry gating internally.
- Current next action after review: `WAIT_FOR_MARKET_OPEN`; next open is Friday 2026-05-29 01:30 Pacific/Auckland and next close is Friday 2026-05-29 08:00 Pacific/Auckland.
- Final pre-automation check for Friday 2026-05-29 run: `./scripts/check.sh` passed, automations are ACTIVE, approved-path preflight/watch probes reached local API and failed closed only because the market is currently closed, with readiness `PAPER-GO`, strategy quality `STRATEGY-QUALITY-OK`, open orders `0`, live routing disabled, and autonomous execution disabled.
- Friday 2026-05-29 review: unattended market-open paper watch finally ran during the 2026-05-28 U.S. session and wrote 30 fresh open-market `EVALUATED` ticks.
- Watch evidence after successful run: total ticks `32`, proposals `0`, blocked/no proposal `32`, audit details `insufficient_liquidity=19`, `insufficient_net_edge_after_costs=12`, `market_closed=1`.
- Post-close evidence confirmed no paper submissions, open paper orders `0`, live routing disabled, autonomous execution disabled, readiness `PAPER-GO`, strategy quality `STRATEGY-QUALITY-OK`, and next action `WAIT_FOR_MARKET_OPEN`.
- Next technical focus: improve/diagnose paper watch signal quality and market-data/liquidity gates before any live funding or live-routing discussion.
- Paper watch quality diagnostic added and generated `PAPER_WATCH_QUALITY_REPORT_2026-05-28.md`; it confirms 30 evaluated open-market ticks, 0 proposals, `insufficient_liquidity=19`, `insufficient_net_edge_after_costs=11`, and no live routing/submission.
- Tonight's next test is scheduled for the U.S. 2026-05-29 session: `market-open-paper-watch` Saturday 2026-05-30 01:30 Pacific/Auckland and `market-close-paper-summary` Saturday 2026-05-30 08:10 Pacific/Auckland.
- Final prep for tonight's run: `./scripts/check.sh` passed, readiness `PAPER-GO`, strategy quality `STRATEGY-QUALITY-OK`, open orders `0`, live routing disabled, autonomous execution disabled; approved-path preflight/watch probes reached local API and failed closed only because the market is currently closed.
- Saturday 2026-05-30 review: second unattended market-open paper watch ran successfully for the U.S. 2026-05-29 open and completed 30/30 iterations.
- Watch evidence after second successful run: total ticks `62`, evaluated ticks `60`, proposals `0`, audit details `insufficient_liquidity=48`, `insufficient_net_edge_after_costs=13`, `market_closed=1`.
- Post-close evidence again confirmed no paper submissions, open paper orders `0`, live routing disabled, autonomous execution disabled, readiness `PAPER-GO`, strategy quality `STRATEGY-QUALITY-OK`, and next action `WAIT_FOR_MARKET_OPEN`.
- Next technical focus remains strategy/market-data quality: two clean paper watch sessions produced no proposals, with the dominant block reason now insufficient liquidity during the opening sample.
- Liquidity gate diagnostic added and generated `PAPER_LIQUIDITY_GATE_REPORT_2026-05-29.md`; for the 2026-05-29 open, evaluated ticks passing volume thresholds were 24/30 at 25k, 19/30 at 50k, 10/30 at 75k, and 1/30 at the current 100k gate. This is diagnostic only and does not lower risk gates.
- Paper gate scenario replay diagnostic added and generated `PAPER_GATE_SCENARIO_REPORT_2026-05-29.md`; candidate minimum-volume gates at 100k, 75k, 50k, and 25k still produced 0 proposals from 30 evaluated events. Lowering liquidity alone would not have created trades because events that passed market gates failed net-edge checks.
- Next paper-market test prepared for the Monday 2026-06-01 U.S. session, which is Tuesday 2026-06-02 in Pacific/Auckland: market open 01:30 and market close 08:00.
- Automation `market-open-paper-watch` is ACTIVE for Tuesday 2026-06-02 01:30 Pacific/Auckland; it runs the guarded QQQ/iex market-open paper watch for 30 iterations with full preflight and closed-market retry handling.
- Automation `market-close-paper-summary` is ACTIVE for Tuesday 2026-06-02 08:10 Pacific/Auckland; it creates the post-close paper summary and morning seed message.
- Final pre-test prep confirmed API LaunchAgent running, Alpaca paper account active, readiness `PAPER-GO`, strategy quality `STRATEGY-QUALITY-OK`, open paper orders `0`, live routing disabled, autonomous execution disabled, and closed-market preflight failing closed only because the market is currently closed.
- Tuesday 2026-06-02 review: unattended market-open paper watch ran successfully for the U.S. 2026-06-01 open and completed 30/30 evaluated iterations.
- Watch evidence after third successful run: total ticks `92`, evaluated ticks `90`, proposals `0`, audit details `insufficient_liquidity=78`, `insufficient_net_edge_after_costs=13`, `market_closed=1`.
- Session-scoped quality report for the latest open confirmed `30`/`30` liquidity blocks, `0` proposals, `volume_max=68550`, and no live routing or submission.
- Post-close evidence confirmed no paper submissions, open paper orders `0`, live routing disabled, autonomous execution disabled, readiness `PAPER-GO`, strategy quality `STRATEGY-QUALITY-OK`, and next action `WAIT_FOR_MARKET_OPEN`.
- Next paper-market window is the U.S. 2026-06-02 session, which is Wednesday 2026-06-03 in Pacific/Auckland: market open 01:30 and market close 08:00.
- Liquidity gate diagnostic generated `PAPER_LIQUIDITY_GATE_REPORT_2026-06-02.md`; for the 2026-06-01 open, evaluated ticks passing volume thresholds were 24/30 at 25k, 13/30 at 50k, 0/30 at 75k, and 0/30 at the current 100k gate.
- Paper gate scenario replay diagnostic generated `PAPER_GATE_SCENARIO_REPORT_2026-06-02.md`; candidate minimum-volume gates at 100k, 75k, 50k, and 25k still produced 0 proposals from 30 evaluated events. At lower thresholds, events that passed liquidity still failed net-edge checks.
- Automation `market-open-paper-watch` is ACTIVE for Wednesday 2026-06-03 01:30 Pacific/Auckland; it runs the guarded QQQ/iex market-open paper watch for 30 iterations with full preflight and closed-market retry handling.
- Automation `market-close-paper-summary` is ACTIVE for Wednesday 2026-06-03 08:10 Pacific/Auckland; it creates the post-close paper summary and morning seed message.
- Wednesday 2026-06-03 review: unattended market-open paper watch ran successfully for the U.S. 2026-06-02 open and completed 30/30 evaluated iterations.
- Watch evidence after fourth successful run: total ticks `122`, evaluated ticks `120`, proposals `0`, audit details `insufficient_liquidity=107`, `insufficient_net_edge_after_costs=14`, `market_closed=1`.
- Session-scoped quality report for the latest open confirmed `29` liquidity blocks, `1` net-edge block, `0` proposals, `volume_max=581718`, and no live routing or submission.
- Post-close evidence confirmed no paper submissions, open paper orders `0`, live routing disabled, autonomous execution disabled, readiness `PAPER-GO`, strategy quality `STRATEGY-QUALITY-OK`, and next action `WAIT_FOR_MARKET_OPEN`.
- Liquidity gate diagnostic generated `PAPER_LIQUIDITY_GATE_REPORT_2026-06-03.md`; for the 2026-06-02 open, evaluated ticks passing volume thresholds were 25/30 at 25k, 20/30 at 50k, 9/30 at 75k, and 1/30 at the current 100k gate.
- Paper gate scenario replay diagnostic generated `PAPER_GATE_SCENARIO_REPORT_2026-06-03.md`; candidate minimum-volume gates at 100k, 75k, 50k, and 25k still produced 0 proposals from 30 evaluated events. At lower thresholds, events that passed liquidity still failed net-edge checks.
- Next paper-market window is the U.S. 2026-06-03 session, which is Thursday 2026-06-04 in Pacific/Auckland: market open 01:30 and market close 08:00.
- Automation `market-open-paper-watch` is ACTIVE for Thursday 2026-06-04 01:30 Pacific/Auckland; it runs the guarded QQQ/iex market-open paper watch for 30 iterations with full preflight and closed-market retry handling.
- Automation `market-close-paper-summary` is ACTIVE for Thursday 2026-06-04 08:10 Pacific/Auckland; it creates the post-close paper summary and morning seed message.
- Thursday 2026-06-04 review: unattended market-open paper watch ran successfully for the U.S. 2026-06-03 open and completed 30/30 evaluated iterations.
- Watch evidence after fifth successful run: total ticks `152`, evaluated ticks `150`, proposals `0`, audit details `insufficient_liquidity=128`, `insufficient_net_edge_after_costs=23`, `market_closed=1`.
- Direct follow-up evidence confirmed no paper submissions, open paper orders `0`, live routing disabled, autonomous execution disabled, readiness `PAPER-GO`, daily ops `PAPER-DAILY-GO`, strategy quality `STRATEGY-QUALITY-OK`, and next action `WAIT_FOR_MARKET_OPEN`.
- Session-scoped quality report for the latest open confirmed `21` liquidity blocks, `9` net-edge blocks, `0` proposals, `volume_max=586617`, and no live routing or submission.
- Liquidity gate diagnostic generated `PAPER_LIQUIDITY_GATE_REPORT_2026-06-04.md`; for the 2026-06-03 open, evaluated ticks passing volume thresholds were 24/30 at 25k, 18/30 at 50k, 14/30 at 75k, and 9/30 at the current 100k gate.
- Paper gate scenario replay diagnostic generated `PAPER_GATE_SCENARIO_REPORT_2026-06-04.md`; candidate minimum-volume gates at 100k, 75k, 50k, and 25k still produced 0 proposals from 30 evaluated events.
- Proposal blocker diagnostic added and generated `PAPER_PROPOSAL_BLOCKER_REPORT_2026-06-04.md`; 9 latest-session ticks passed current liquidity, but expected edge was `5.04 bps` versus the configured `9.0 bps` requirement, leaving a consistent `3.96 bps` edge shortfall.
- Next paper-market window is the U.S. 2026-06-04 session, which is Friday 2026-06-05 in Pacific/Auckland: market open 01:30 and market close 08:00.
- Automation `market-open-paper-watch` is ACTIVE for Friday 2026-06-05 01:30 Pacific/Auckland; it runs the guarded QQQ/iex market-open paper watch for 30 iterations with full preflight and closed-market retry handling.
- Automation `market-close-paper-summary` is ACTIVE for Friday 2026-06-05 08:10 Pacific/Auckland; it creates the post-close paper summary and morning seed message.
- Friday 2026-06-05 review: unattended market-open paper watch ran successfully for the U.S. 2026-06-04 open and completed 30/30 evaluated iterations.
- Watch evidence after sixth successful run: total ticks `182`, evaluated ticks `180`, proposals `0`, audit details `insufficient_liquidity=147`, `insufficient_net_edge_after_costs=34`, `market_closed=1`.
- Post-close evidence confirmed no paper submissions, open paper orders `0`, live routing disabled, autonomous execution disabled, readiness `PAPER-GO`, daily ops `PAPER-DAILY-GO`, strategy quality `STRATEGY-QUALITY-OK`, and next action `WAIT_FOR_MARKET_OPEN`.
- Session-scoped quality report for the latest open confirmed `19` liquidity blocks, `11` net-edge blocks, `0` proposals, `volume_max=142287`, and no live routing or submission.
- Liquidity gate diagnostic generated `PAPER_LIQUIDITY_GATE_REPORT_2026-06-05.md`; for the 2026-06-04 open, evaluated ticks passing volume thresholds were 26/30 at 25k, 21/30 at 50k, 16/30 at 75k, and 11/30 at the current 100k gate.
- Paper gate scenario replay diagnostic generated `PAPER_GATE_SCENARIO_REPORT_2026-06-05.md`; candidate minimum-volume gates at 100k, 75k, 50k, and 25k still produced 0 proposals from 30 evaluated events.
- Proposal blocker diagnostic generated `PAPER_PROPOSAL_BLOCKER_REPORT_2026-06-05.md`; 11 latest-session ticks passed current liquidity, but expected edge was `5.04 bps` versus the configured `9.0 bps` requirement, leaving a consistent `3.96 bps` edge shortfall.
- Read-only paper watchlist support added and tested in the proven `run_market_open_paper_watch.py` launcher via `--symbols`; it runs one full market-open preflight, then cycles through a configurable symbol list with `auto_submit_enabled=false`; a closed-market probe failed closed with `session_plan=MARKET-CLOSED-WAIT`.
- Next paper-market window is the U.S. 2026-06-05 session, which is Saturday 2026-06-06 in Pacific/Auckland: market open `2026-06-06 01:30` and market close `2026-06-06 08:00`.
- Automation `market-open-paper-watch` is ACTIVE for Saturday 2026-06-06 01:30 Pacific/Auckland; it runs the guarded SPY/QQQ/AAPL/MSFT/NVDA iex paper watchlist for 30 cycles with full preflight and closed-market retry handling.
- Automation `market-close-paper-summary` is ACTIVE for Saturday 2026-06-06 08:10 Pacific/Auckland; it creates the post-close paper summary, symbol coverage summary, proposal blocker report, and morning seed message.
- Morning review on Saturday 2026-06-06 confirmed no new overnight paper watch/watchlist evidence for the Friday 2026-06-05 U.S. session; `logs/paper_watch_history.jsonl` still ends at `2026-06-04T14:01:23.427658+00:00`, so the latest open-market sample remains the Thursday 2026-06-04 U.S. open.
- Root cause of the missed Friday U.S. watchlist run: the first standalone watchlist launcher path failed closed in automation with sandboxed local-API network access. The fix was to move watchlist support into the already proven `run_market_open_paper_watch.py` path and verify a clean closed-market fail-closed probe with `--symbols SPY,QQQ,AAPL,MSFT,NVDA`.
- Current post-close state is still paper-only and green: readiness `PAPER-GO`, daily ops `PAPER-DAILY-GO`, strategy quality `STRATEGY-QUALITY-OK`, open paper orders `0`, live routing disabled, autonomous execution disabled, and next action `WAIT_FOR_MARKET_OPEN` for Monday 2026-06-09 01:30 Pacific/Auckland.
- Fresh evidence generated for operator review: `PAPER_WATCH_REPORT_2026-06-05.md`, `PAPER_OPS_EVIDENCE_2026-06-05.md`, `PAPER_GO_NO_GO_CHECKLIST_2026-06-05.md`, and `POST_MARKET_CLOSE_PAPER_SUMMARY_2026-06-06.md`; latest unchanged session diagnostics remain `PAPER_WATCH_QUALITY_REPORT_2026-06-04.md` and `PAPER_PROPOSAL_BLOCKER_REPORT_2026-06-05.md`.
- Automation `market-open-paper-watch` is ACTIVE for Tuesday 2026-06-09 01:30 Pacific/Auckland; it runs `.venv/bin/python scripts/run_market_open_paper_watch.py --symbols SPY,QQQ,AAPL,MSFT,NVDA --feed iex --interval-seconds 60 --iterations 30`.
- Automation `market-close-paper-summary` is ACTIVE for Tuesday 2026-06-09 08:10 Pacific/Auckland; it creates the post-close paper summary, symbol coverage summary, proposal blocker report, and morning seed message.
- Tuesday 2026-06-09 review: the watchlist automation failed closed before running ticks because its RRULE was interpreted as UTC, so `BYHOUR=1` fired at `13:30 Pacific/Auckland` while the U.S. market was closed. No new watch ticks or proposals were recorded.
- Corrected automation schedule uses UTC equivalents for the next U.S. session: `market-open-paper-watch` is ACTIVE for Tuesday 2026-06-09 13:30 UTC, which is Wednesday 2026-06-10 01:30 Pacific/Auckland; `market-close-paper-summary` is ACTIVE for Tuesday 2026-06-09 20:10 UTC, which is Wednesday 2026-06-10 08:10 Pacific/Auckland.
- Current state after correction: readiness `PAPER-GO`, daily ops `PAPER-DAILY-GO`, strategy quality `STRATEGY-QUALITY-OK`, open paper orders `0`, live routing disabled, autonomous execution disabled, and next action `WAIT_FOR_MARKET_OPEN`.
- Fresh evidence generated for this correction review: `PAPER_WATCH_REPORT_2026-06-09.md`, `PAPER_OPS_EVIDENCE_2026-06-09.md`, `PAPER_GO_NO_GO_CHECKLIST_2026-06-09.md`, and `POST_MARKET_CLOSE_PAPER_SUMMARY_2026-06-09.md`.
- Strategy proposal blocker fix added on 2026-06-09: Alpaca market snapshots now carry `intraday_change_bps` from daily open to current price, and `SimpleMomentumStrategy` uses that observable intraday momentum before falling back to the older volatility proxy.
- Updated synthetic evidence generated `PAPER_STRATEGY_SCENARIO_REPORT_2026-06-09.md`; scenario `intraday_momentum_reaches_manual_review` creates a manual-review paper proposal with expected edge `10.818182 bps`, clearing the configured `9.0 bps` requirement without changing liquidity, spread, net-edge, live-routing, or auto-submit guardrails.
- `strategy_quality_report.py` now reports max theoretical intraday edge `14.0 bps`, required edge `9.0 bps`, and status `STRATEGY-QUALITY-OK`.
- Wednesday 2026-06-10 review confirmed the corrected overnight watch succeeded: `332` total ticks, `330` evaluated ticks, and `19` manual-review paper proposals across AAPL/NVDA while auto-submit stayed disabled and live routing stayed off.
- Corrected diagnostic reports generated `PAPER_WATCH_QUALITY_REPORT_2026-06-09.md` and `PAPER_PROPOSAL_BLOCKER_REPORT_2026-06-09.md`; both now identify proposal generation as cleared for this sample, with remaining blocks treated as residual gate diagnostics.
- Representative sizing blocker identified: the successful overnight run used Alpaca's `$100,000` paper account, so proposal notionals were sized around the paper-account risk budget rather than the intended `$100 USD` live seed capital.
- Watch launchers now support `--simulated-equity`; next automation is ACTIVE for Wednesday 2026-06-10 13:30 UTC, which is Thursday 2026-06-11 01:30 Pacific/Auckland, and runs `.venv/bin/python scripts/run_market_open_paper_watch.py --symbols SPY,QQQ,AAPL,MSFT,NVDA --feed iex --interval-seconds 60 --iterations 30 --simulated-equity 100`.
- Matching post-close summary automation is ACTIVE for Wednesday 2026-06-10 20:10 UTC, which is Thursday 2026-06-11 08:10 Pacific/Auckland.
- Thursday 2026-06-11 review confirmed the `$100` simulated-equity watch succeeded: `150` evaluated ticks produced `28` manual-review proposals, with proposal notionals from `$1.301572` to `$2.00` and expected edge from `9.111003` to `14.0` bps.
- Latest-session proposal distribution was `23` BUY and `5` SELL. Alpaca documentation confirms fractional orders can start at `$1`, but fractional short sales are not supported.
- Launch-stage long-only hardening added: `allow_short_sales=false` by default; naked SELL orders and SELL quantities above owned positions are blocked by the safety engine; the manual paper-submit endpoint rejects SELL requests while short sales are disabled.
- Evidence generated: `PAPER_WATCH_REPORT_2026-06-10.md`, `POST_MARKET_CLOSE_PAPER_SUMMARY_2026-06-10.md`, and `PAPER_CAPITAL_PROFILE_REPORT_2026-06-10.md`.
- LaunchAgent `com.aiinvesting.api` was reinstalled after commit `c8af4ce`; the running API now includes the long-only guard and reports `ALPACA-PAPER-READY`.
- Final long-only market validation automation is ACTIVE for Thursday 2026-06-11 13:30 UTC, which is Friday 2026-06-12 01:30 Pacific/Auckland; the matching summary is ACTIVE for Thursday 2026-06-11 20:10 UTC, which is Friday 2026-06-12 08:10 Pacific/Auckland.
- Friday 2026-06-12 review found the unattended watch was safe but partial: `35` ticks (`7` of `30` cycles) completed before the automation runtime window ended. The partial sample had no proposals because opening liquidity and spreads blocked signals first.
- Full deterministic replay of all `150` ticks from the proposal-bearing `2026-06-10` `$100` session through current long-only code produced `23` BUY manual-review proposals, `0` SELL proposals, and `5` `short_sale_disabled` blocks. Evidence: `PAPER_LONG_ONLY_REPLAY_REPORT_2026-06-12.md`.
- Current readiness remains `PAPER-GO` with `11/11` checks passing and open paper orders `0`.
- Corrected final unattended watch is ACTIVE for Friday 2026-06-12 13:45 UTC, which is Saturday 2026-06-13 01:45 Pacific/Auckland. It starts 15 minutes after the U.S. open and runs `15` cycles at `10`-second intervals to finish within the job window. Matching summary is scheduled for Saturday 2026-06-13 08:10 Pacific/Auckland.

## Evidence Files

- `OPERATIONS_SNAPSHOT_2026-05-22.md`
- `ALPACA_PAPER_VERIFICATION_2026-05-22.md`
- `PAPER_ORDER_SUBMISSION_2026-05-22.md`
- `PAPER_ORDER_RECONCILIATION_2026-05-22.md`
- `PAPER_ORDER_CANCEL_2026-05-22.md`
- `PAPER_MARKET_DATA_PREVIEW_2026-05-23.md`
- `PAPER_DRY_RUN_DRILL_2026-05-23.md`
- `PAPER_OPS_EVIDENCE_2026-05-23.md`
- `PAPER_WATCH_REPORT_2026-05-23.md`
- `PAPER_OPS_EVIDENCE_2026-05-24.md`
- `PAPER_WATCH_REPORT_2026-05-24.md`
- `PAPER_STRATEGY_SCENARIO_REPORT_2026-05-24.md`
- `PAPER_GO_NO_GO_CHECKLIST_2026-05-24.md`
- `SCALING_POLICY_REPORT_2026-05-25.md`
- `PAPER_OPS_EVIDENCE_2026-05-25.md`
- `PAPER_WATCH_REPORT_2026-05-25.md`
- `PAPER_GO_NO_GO_CHECKLIST_2026-05-25.md`
- `PAPER_OPS_EVIDENCE_2026-05-26.md`
- `PAPER_WATCH_REPORT_2026-05-26.md`
- `PAPER_GO_NO_GO_CHECKLIST_2026-05-26.md`
- `POST_MARKET_CLOSE_PAPER_SUMMARY_2026-05-27.md`
- `PAPER_OPS_EVIDENCE_2026-05-27.md`
- `PAPER_WATCH_REPORT_2026-05-27.md`
- `PAPER_GO_NO_GO_CHECKLIST_2026-05-27.md`
- `POST_MARKET_CLOSE_PAPER_SUMMARY_2026-05-28.md`
- `PAPER_OPS_EVIDENCE_2026-05-28.md`
- `PAPER_WATCH_REPORT_2026-05-28.md`
- `PAPER_WATCH_QUALITY_REPORT_2026-05-28.md`
- `PAPER_GO_NO_GO_CHECKLIST_2026-05-28.md`
- `POST_MARKET_CLOSE_PAPER_SUMMARY_2026-05-29.md`
- `PAPER_OPS_EVIDENCE_2026-05-29.md`
- `PAPER_WATCH_REPORT_2026-05-29.md`
- `PAPER_WATCH_QUALITY_REPORT_2026-05-29.md`
- `PAPER_LIQUIDITY_GATE_REPORT_2026-05-29.md`
- `PAPER_GATE_SCENARIO_REPORT_2026-05-29.md`
- `PAPER_GO_NO_GO_CHECKLIST_2026-05-29.md`
- `POST_MARKET_CLOSE_PAPER_SUMMARY_2026-05-30.md`
- `PAPER_WATCH_REPORT_2026-06-01.md`
- `PAPER_WATCH_QUALITY_REPORT_2026-06-01.md`
- `PAPER_OPS_EVIDENCE_2026-06-01.md`
- `PAPER_GO_NO_GO_CHECKLIST_2026-06-01.md`
- `POST_MARKET_CLOSE_PAPER_SUMMARY_2026-06-02.md`
- `PAPER_LIQUIDITY_GATE_REPORT_2026-06-02.md`
- `PAPER_GATE_SCENARIO_REPORT_2026-06-02.md`
- `PAPER_WATCH_REPORT_2026-06-02.md`
- `PAPER_WATCH_QUALITY_REPORT_2026-06-02.md`
- `PAPER_OPS_EVIDENCE_2026-06-02.md`
- `PAPER_GO_NO_GO_CHECKLIST_2026-06-02.md`
- `POST_MARKET_CLOSE_PAPER_SUMMARY_2026-06-03.md`
- `PAPER_LIQUIDITY_GATE_REPORT_2026-06-03.md`
- `PAPER_GATE_SCENARIO_REPORT_2026-06-03.md`
- `PAPER_WATCH_REPORT_2026-06-04.md`
- `PAPER_WATCH_QUALITY_REPORT_2026-06-03.md`
- `PAPER_OPS_EVIDENCE_2026-06-04.md`
- `PAPER_GO_NO_GO_CHECKLIST_2026-06-03.md`
- `POST_MARKET_CLOSE_PAPER_SUMMARY_2026-06-04.md`
- `PAPER_LIQUIDITY_GATE_REPORT_2026-06-04.md`
- `PAPER_GATE_SCENARIO_REPORT_2026-06-04.md`
- `PAPER_PROPOSAL_BLOCKER_REPORT_2026-06-04.md`
- `PAPER_WATCH_REPORT_2026-06-04.md`
- `PAPER_WATCH_QUALITY_REPORT_2026-06-04.md`
- `PAPER_OPS_EVIDENCE_2026-06-04.md`
- `PAPER_GO_NO_GO_CHECKLIST_2026-06-04.md`
- `POST_MARKET_CLOSE_PAPER_SUMMARY_2026-06-05.md`
- `PAPER_LIQUIDITY_GATE_REPORT_2026-06-05.md`
- `PAPER_GATE_SCENARIO_REPORT_2026-06-05.md`
- `PAPER_PROPOSAL_BLOCKER_REPORT_2026-06-05.md`
- `PAPER_GO_NO_GO_CHECKLIST_2026-06-05.md`
- `PAPER_WATCH_REPORT_2026-06-09.md`
- `PAPER_OPS_EVIDENCE_2026-06-09.md`
- `PAPER_GO_NO_GO_CHECKLIST_2026-06-09.md`
- `POST_MARKET_CLOSE_PAPER_SUMMARY_2026-06-09.md`
- `PAPER_STRATEGY_SCENARIO_REPORT_2026-06-09.md`
- `PAPER_WATCH_QUALITY_REPORT_2026-06-09.md`
- `PAPER_PROPOSAL_BLOCKER_REPORT_2026-06-09.md`
- `PAPER_WATCH_REPORT_2026-06-10.md`
- `POST_MARKET_CLOSE_PAPER_SUMMARY_2026-06-10.md`
- `PAPER_CAPITAL_PROFILE_REPORT_2026-06-10.md`
- `POST_MARKET_CLOSE_PAPER_SUMMARY_2026-06-11.md`
- `PAPER_LONG_ONLY_REPLAY_REPORT_2026-06-12.md`

## First Commands Tomorrow

If unattended automations ran overnight, first inspect their outputs in Codex and then run:

```bash
cd "/Users/michielburger/Claude Code/AI-investing-system"
git status --short --branch
./scripts/check.sh
.venv/bin/python scripts/verify_macos_apps.py
.venv/bin/python scripts/check_alpaca_market_data.py
curl -s http://127.0.0.1:8001/dashboard/summary -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/account" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/clock" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
.venv/bin/python scripts/paper_market_session_plan.py
curl -s "http://127.0.0.1:8001/broker/paper/session_plan" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/orders?status=open&limit=20" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/strategy_preview?symbol=QQQ&feed=iex&use_paper_account=true" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
.venv/bin/python scripts/paper_market_open_preflight.py
.venv/bin/python scripts/paper_next_action.py
curl -s "http://127.0.0.1:8001/broker/paper/market_open_preflight" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/next_action" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
.venv/bin/python scripts/run_market_open_paper_watch.py --symbols SPY,QQQ,AAPL,MSFT,NVDA --feed iex --interval-seconds 60 --iterations 30
.venv/bin/python scripts/run_paper_watch.py --symbol QQQ --feed iex --interval-seconds 5 --iterations 1
curl -s "http://127.0.0.1:8001/broker/paper/watch_history?limit=5" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/watch_summary?limit=500" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
.venv/bin/python scripts/paper_watch_report.py
curl -s "http://127.0.0.1:8001/broker/paper/watch_export?format=csv&limit=5" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
.venv/bin/python scripts/paper_readiness_report.py
.venv/bin/python scripts/strategy_quality_report.py
.venv/bin/python scripts/scaling_policy_report.py --write-report
.venv/bin/python scripts/paper_strategy_scenarios.py --write-report
.venv/bin/python scripts/paper_go_no_go_checklist.py
.venv/bin/python scripts/paper_daily_ops.py
.venv/bin/python scripts/paper_ops_snapshot.py
.venv/bin/python scripts/paper_ops_evidence.py
curl -s "http://127.0.0.1:8001/broker/paper/readiness?watch_limit=500" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/strategy_quality" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/strategy_scenarios" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/go_no_go_checklist" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/ops_snapshot?watch_limit=500" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
.venv/bin/python scripts/paper_order_drill.py
curl -s -X POST http://127.0.0.1:8001/broker/paper/order_drill -H "Content-Type: application/json" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)" -d '{"symbol":"QQQ","side":"BUY","quantity":0.001,"limit_price":1.00}'
```

## Next Technical Goal

Continue real-time paper trading, not live trading:

1. Run market-hours paper watch sessions after Alpaca clock reports open.
2. Improve strategy signal quality before any live trading discussion.
3. Keep paper submit manual-only behind exact confirmation phrase.
4. Run paper submit/reconcile/cancel drill again only with explicit operator approval.
5. Prepare paper-trading GO/NO-GO checklist before any live discussion.
6. Continue strategy-quality improvements only in paper/watch mode.

## Boundaries

- Do not enable live credentials.
- Do not enable live routing.
- Do not enable autonomous broker submission.
- Do not submit paper orders automatically from the strategy pipeline until a separate GO decision.
