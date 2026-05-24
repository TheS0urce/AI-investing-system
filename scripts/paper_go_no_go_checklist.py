from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def checklist_items() -> list[dict[str, str]]:
    return [
        {
            "gate": "API is running",
            "command": "curl http://127.0.0.1:8001/health",
            "go_condition": "Response status is ok.",
        },
        {
            "gate": "Broker is paper-ready",
            "command": ".venv/bin/python scripts/check_alpaca_paper_account.py",
            "go_condition": "Status is ALPACA-PAPER-ACCOUNT-OK.",
        },
        {
            "gate": "Live routing is disabled",
            "command": "curl http://127.0.0.1:8001/broker/status -H \"X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)\"",
            "go_condition": "Mode is paper and live_enabled is false.",
        },
        {
            "gate": "Daily ops is green",
            "command": ".venv/bin/python scripts/paper_daily_ops.py",
            "go_condition": "Status is PAPER-DAILY-GO.",
        },
        {
            "gate": "Strategy quality is acceptable",
            "command": ".venv/bin/python scripts/strategy_quality_report.py",
            "go_condition": "Status is STRATEGY-QUALITY-OK.",
        },
        {
            "gate": "Scenario evidence is current",
            "command": ".venv/bin/python scripts/paper_strategy_scenarios.py --write-report",
            "go_condition": "Report confirms no auto-submit and no live trading approval.",
        },
        {
            "gate": "Market session is open",
            "command": ".venv/bin/python scripts/paper_market_session_plan.py",
            "go_condition": "Status is MARKET-OPEN-RUN-WATCH.",
        },
        {
            "gate": "No open paper orders",
            "command": ".venv/bin/python scripts/list_alpaca_paper_orders.py --status open --limit 20",
            "go_condition": "Open order list is empty before starting a watch session.",
        },
        {
            "gate": "Read-only watch evidence captured",
            "command": ".venv/bin/python scripts/run_paper_watch.py --symbol QQQ --feed iex --interval-seconds 60 --iterations 30",
            "go_condition": "Watch completes without auto-submit and writes history.",
        },
        {
            "gate": "Watch report written",
            "command": ".venv/bin/python scripts/paper_watch_report.py",
            "go_condition": "Report shows proposals, blocks, and watch statuses for review.",
        },
    ]


def format_checklist(generated_at: str) -> str:
    lines = [
        f"# Paper Trading GO/NO-GO Checklist - {generated_at[:10]}",
        "",
        "## Hard Guards",
        "",
        "- Paper mode only.",
        "- Live routing must remain disabled.",
        "- Autonomous execution must remain disabled.",
        "- Manual approval must remain required.",
        "- Do not submit a paper order unless the operator explicitly approves it.",
        "",
        "## Gates",
        "",
    ]
    for index, item in enumerate(checklist_items(), start=1):
        lines.extend(
            [
                f"### {index}. {item['gate']}",
                "",
                f"- Command: `{item['command']}`",
                f"- GO condition: {item['go_condition']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Stop Conditions",
            "",
            "- Any command returns NO-GO, FAIL, 401, or network errors.",
            "- Any status reports live_enabled as true.",
            "- Any unexpected open order appears before the session.",
            "- The market is closed unless the session is explicitly a closed-market dry run.",
            "",
        ]
    )
    return "\n".join(lines)


def default_output_path(generated_at: str) -> Path:
    return ROOT / f"PAPER_GO_NO_GO_CHECKLIST_{generated_at[:10]}.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the paper trading GO/NO-GO operator checklist.")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    generated_at = datetime.now(timezone.utc).isoformat()
    output_path = args.output or default_output_path(generated_at)
    output_path.write_text(format_checklist(generated_at), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PAPER-GO-NO-GO-CHECKLIST-READY",
                "output": str(output_path),
                "gate_count": len(checklist_items()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
