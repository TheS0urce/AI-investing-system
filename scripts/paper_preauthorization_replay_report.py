from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from paper_watch_quality_report import HISTORY_PATH, ROOT, filter_events, load_history

sys.path.insert(0, str(ROOT))

from src.ai_investing.models import OrderProposal, Side
from src.ai_investing.preauthorization import (
    AuthorizationContext,
    PreauthorizationPolicy,
    PreauthorizationState,
    authorize_entry,
)


def proposal_from_event(event: dict[str, Any]) -> OrderProposal | None:
    payload = event.get("order_proposal")
    if not isinstance(payload, dict):
        return None
    try:
        return OrderProposal(
            symbol=str(payload["symbol"]).upper(),
            side=Side(str(payload["side"]).upper()),
            quantity=float(payload["quantity"]),
            limit_price=float(payload["limit_price"]),
            expected_edge_bps=float(payload["expected_edge_bps"]),
            reason=str(payload.get("reason", "historical replay")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def build_preauthorization_replay_report(
    events: list[dict[str, Any]],
    *,
    since: str | None = None,
    policy: PreauthorizationPolicy | None = None,
) -> dict[str, object]:
    policy = policy or PreauthorizationPolicy()
    replay_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    state = PreauthorizationState(
        active=True,
        activated_at=replay_time.isoformat(),
        expires_at=(replay_time + timedelta(hours=policy.lease_hours)).isoformat(),
        paper_only=True,
    )
    filtered = filter_events(events, since)
    proposals = [(event, proposal_from_event(event)) for event in filtered]
    proposals = [(event, order) for event, order in proposals if order is not None]
    reasons: Counter[str] = Counter()
    eligible: list[dict[str, object]] = []

    for event, order in proposals:
        market = event.get("market") if isinstance(event.get("market"), dict) else {}
        spread_bps = float(market.get("spread_bps", 0.0) or 0.0)
        decision = authorize_entry(
            order,
            spread_bps=spread_bps,
            state=state,
            context=AuthorizationContext(
                broker_mode="paper",
                live_enabled=False,
                market_is_open=True,
                session_date="2026-01-01",
                gross_exposure_usd=0.0,
                daily_realized_pnl_usd=0.0,
            ),
            policy=policy,
            now=replay_time,
        )
        reasons[decision.reason] += 1
        if decision.approved:
            eligible.append(
                {
                    "at": event.get("at"),
                    "symbol": order.symbol,
                    "notional_usd": round(order.quantity * order.limit_price, 6),
                    "expected_edge_bps": order.expected_edge_bps,
                    "spread_bps": spread_bps,
                }
            )

    notionals = [float(item["notional_usd"]) for item in eligible]
    symbols = Counter(str(item["symbol"]) for item in eligible)
    return {
        "status": "PAPER-PREAUTHORIZATION-REPLAY-READY",
        "scope": "historical_read_only_policy_replay",
        "since": since,
        "proposal_count": len(proposals),
        "eligible_count": len(eligible),
        "eligible_symbols": dict(sorted(symbols.items())),
        "decision_reasons": dict(sorted(reasons.items())),
        "eligible_notional_min_usd": min(notionals) if notionals else None,
        "eligible_notional_max_usd": max(notionals) if notionals else None,
        "policy": {
            "paper_only": policy.paper_only,
            "long_only": policy.long_only,
            "max_order_notional_usd": policy.max_order_notional_usd,
            "max_entries_per_session": policy.max_entries_per_session,
            "max_gross_exposure_usd": policy.max_gross_exposure_usd,
            "max_daily_loss_usd": policy.max_daily_loss_usd,
            "max_order_capital_pct": policy.max_order_capital_pct,
            "max_gross_exposure_capital_pct": policy.max_gross_exposure_capital_pct,
            "max_daily_loss_capital_pct": policy.max_daily_loss_capital_pct,
            "minimum_expected_edge_bps": policy.minimum_expected_edge_bps,
            "max_spread_bps": policy.max_spread_bps,
        },
        "authorization_activated": False,
        "paper_orders_submitted": 0,
        "live_trading_approved": False,
        "broker_fractional_bracket_verified": False,
        "conclusion": (
            "Historical BUY proposals fit the bounded policy envelope."
            if eligible
            else "No historical proposal fit the bounded policy envelope."
        ),
    }


def format_markdown_report(report: dict[str, object], generated_at: str) -> str:
    symbols = report.get("eligible_symbols") if isinstance(report.get("eligible_symbols"), dict) else {}
    reasons = report.get("decision_reasons") if isinstance(report.get("decision_reasons"), dict) else {}
    symbol_lines = [f"- {symbol}: `{count}`" for symbol, count in symbols.items()] or ["- none: `0`"]
    reason_lines = [f"- {reason}: `{count}`" for reason, count in reasons.items()] or ["- none: `0`"]
    return "\n".join(
        [
            f"# Paper Preauthorization Replay Report - {generated_at[:10]}",
            "",
            "## Scope",
            "",
            "This is a read-only replay of recorded paper proposals through the bounded preauthorization policy. It does not activate authorization or submit an order.",
            "",
            "## Results",
            "",
            f"- Historical proposals: `{report.get('proposal_count')}`",
            f"- Eligible proposals: `{report.get('eligible_count')}`",
            f"- Eligible notional range: `${report.get('eligible_notional_min_usd')}` to `${report.get('eligible_notional_max_usd')}`",
            "",
            "## Eligible Symbols",
            "",
            *symbol_lines,
            "",
            "## Decisions",
            "",
            *reason_lines,
            "",
            "## Guardrails",
            "",
            f"- Authorization activated: `{report.get('authorization_activated')}`",
            f"- Paper orders submitted: `{report.get('paper_orders_submitted')}`",
            f"- Live trading approved: `{report.get('live_trading_approved')}`",
            f"- Fractional bracket verified by broker: `{report.get('broker_fractional_bracket_verified')}`",
            "",
            "## Conclusion",
            "",
            str(report.get("conclusion")),
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay paper proposals through bounded preauthorization.")
    parser.add_argument("--since", default=None)
    parser.add_argument("--history", type=Path, default=HISTORY_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    report = build_preauthorization_replay_report(load_history(args.history), since=args.since)
    if args.write_report or args.output is not None:
        generated_at = datetime.now(timezone.utc).isoformat()
        output = args.output or ROOT / f"PAPER_PREAUTHORIZATION_REPLAY_REPORT_{generated_at[:10]}.md"
        output.write_text(format_markdown_report(report, generated_at), encoding="utf-8")
        print(json.dumps({"status": report["status"], "output": str(output)}, indent=2))
        return 0
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
