#!/usr/bin/env python3
"""Fail-closed preflight for a future automated forecast generator.

Does not regenerate predictions, modify model weights, or publish data.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
FILES = ("live-v2.json", "simulations.json", "player-research.json")
def main():
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "ready_for_automatic_publication": False, "files": {}, "blockers": []}
    for name in FILES:
        path = DATA / name
        if not path.is_file() or not path.stat().st_size:
            report["files"][name] = "missing_or_empty"
            report["blockers"].append(f"{name}: no usable source data")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            report["files"][name] = "invalid_json"
            report["blockers"].append(f"{name}: {type(exc).__name__}")
            continue
        if not isinstance(data, (dict, list)) or not data:
            report["blockers"].append(f"{name}: empty or invalid top-level data")
        report["files"][name] = "valid_json"
    report["blockers"].append("No verified production prediction generator wired into refresh workflow")
    print(json.dumps(report, indent=2))
    # Inspection-only: missing data is reported but cannot overwrite existing predictions.
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
