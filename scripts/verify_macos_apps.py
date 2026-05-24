from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_APPS = [
    "AI Investing Start API.app",
    "AI Investing Health.app",
    "AI Investing Dashboard.app",
    "AI Investing Daily Ops.app",
    "AI Investing Market Preflight.app",
    "AI Investing Next Action.app",
    "AI Investing Stop API.app",
]


def verify_launchers(dest_dir: Path) -> dict[str, object]:
    apps = []
    missing = []
    for app_name in EXPECTED_APPS:
        path = dest_dir / app_name
        entry = {
            "name": app_name,
            "path": str(path),
            "exists": path.exists(),
            "is_app_bundle": (path / "Contents" / "Info.plist").exists(),
        }
        apps.append(entry)
        if not entry["exists"] or not entry["is_app_bundle"]:
            missing.append(app_name)

    return {
        "status": "LAUNCHERS-READY" if not missing else "LAUNCHERS-NO-GO",
        "destination": str(dest_dir),
        "expected_count": len(EXPECTED_APPS),
        "ready_count": len(EXPECTED_APPS) - len(missing),
        "missing": missing,
        "apps": apps,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify AI Investing Mac launcher apps are installed.")
    parser.add_argument(
        "destination",
        nargs="?",
        type=Path,
        default=Path.home() / "Applications" / "AI Investment",
    )
    args = parser.parse_args()

    result = verify_launchers(args.destination)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "LAUNCHERS-READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
