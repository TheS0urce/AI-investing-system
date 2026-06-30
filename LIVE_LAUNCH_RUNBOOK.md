# Bounded Live Launch Runbook

## Current State

The live path is implemented but disabled. Paper and live credentials, authorization
state, protective-exit state, watch history, endpoints, and schedulers are separate.
No live order can be submitted from the default repository configuration.

## Initial Envelope

- Expected account value: `$300`, with a preflight tolerance of `$250-$350`
- Maximum entry at launch: `4%` of verified equity (`$12` at `$300`)
- Maximum entries per session: `2`
- Maximum gross exposure at launch: `8%` of verified equity (`$24` at `$300`)
- Maximum daily realized loss: lower of `$3` or `1%` of verified equity
- Long-only approved symbols: `SPY`, `QQQ`, `AAPL`, `MSFT`, `NVDA`
- Regular U.S. market hours only
- Minimum expected edge: `9 bps`
- Maximum spread: `30 bps`
- Stop loss: `1.5%`
- Take profit: `3%`
- Maximum holding time: `6 hours`
- Live authorization lease: `24 hours`
- Qualified 20-trade performance windows increase opportunity limits by `10%`,
  up to three steps; losses and drawdown tighten or pause them

## One-Time Account Preparation

1. Complete Alpaca live-account approval.
2. Deposit approximately `$300 USD`.
3. Confirm there are no manually opened positions or orders.
4. Generate live API credentials that are distinct from paper credentials.
5. Run `./scripts/configure_alpaca_live.sh`.
6. Restart with `./scripts/install_launch_agent.sh`.
7. Check `GET /broker/live/readiness`; it must return `LIVE-PREFLIGHT-GO`.

The production domain is fixed to `https://api.alpaca.markets`. Any other live base
URL fails closed.

## First Session

1. Review the masked account, portfolio value, open orders, and open positions from
   `GET /broker/live/readiness`.
2. Activate the bounded lease with the exact phrase `AUTHORIZE_BOUNDED_LIVE`.
3. Confirm `GET /broker/live/authorization` reports `ACTIVE`.
4. Run `./scripts/install_live_watch_agent.sh`.
5. Confirm `launchctl list com.aiinvesting.live-watch` reports exit status `0`.
6. Review `logs/live_watch_agent.log` after the session.

The installer refuses to run unless preflight is green and authorization is active.
It disables the paper watch when the live watch is installed.

## Automated Behavior

- Checks protective exits every five minutes and during every live watch cycle.
- Waits until 9:45 a.m. New York time before seeking entries.
- Retries zero-proposal windows until 11:30 a.m. New York time.
- Stops after two bounded entry submissions.
- Tracks submitted exits until Alpaca confirms a fill.
- Re-queues rejected, canceled, expired, or suspended exits.
- Pauses new entries after any operational error.
- Continues protective-exit checks even after the entry lease expires.

## Emergency Stop

Call `POST /broker/live/emergency_stop` with:

```json
{"confirm": "STOP_LIVE_TRADING"}
```

This immediately revokes entry authorization and requests cancellation of open
orders. Existing positions remain under the protective-exit manager; it does not
blindly liquidate at an unknown price.

## Reauthorization

The lease expires after 24 hours. A later session requires a fresh preflight and the
exact phrase `AUTHORIZE_BOUNDED_LIVE`. Limits cannot expand automatically until the
configured performance window is satisfied.
