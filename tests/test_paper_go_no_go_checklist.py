import importlib.util
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location("paper_go_no_go_checklist", SCRIPTS_DIR / "paper_go_no_go_checklist.py")
paper_go_no_go_checklist = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(paper_go_no_go_checklist)


def test_checklist_includes_paper_only_hard_guards():
    markdown = paper_go_no_go_checklist.format_checklist("2026-05-24T12:00:00+00:00")

    assert "# Paper Trading GO/NO-GO Checklist - 2026-05-24" in markdown
    assert "Paper mode only." in markdown
    assert "Live routing must remain disabled." in markdown
    assert "Autonomous execution must remain disabled." in markdown
    assert "Manual approval must remain required." in markdown
    assert "Do not submit a paper order unless the operator explicitly approves it." in markdown


def test_checklist_includes_market_and_evidence_gates():
    items = {item["gate"]: item for item in paper_go_no_go_checklist.checklist_items()}

    assert items["Market session is open"]["go_condition"] == "Status is MARKET-OPEN-RUN-WATCH."
    assert items["Market-open preflight passes"]["go_condition"] == "Status is PAPER-MARKET-OPEN-GO."
    assert "paper_daily_ops.py" in items["Daily ops is green"]["command"]
    assert "paper_strategy_scenarios.py --write-report" in items["Scenario evidence is current"]["command"]
    assert "run_market_open_paper_watch.py" in items["Read-only watch evidence captured"]["command"]
    assert "SPY,QQQ,AAPL,MSFT,NVDA" in items["Read-only watch evidence captured"]["command"]
    assert "Full PAPER-MARKET-OPEN-GO preflight passes" in items["Read-only watch evidence captured"]["go_condition"]
