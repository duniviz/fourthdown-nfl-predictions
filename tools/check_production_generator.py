#!/usr/bin/env python3
"""Fail closed until the real production generator and player schemas exist."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [ROOT / "production" / "generate.py",
            ROOT / "production" / "validate_player_candidates.py",
            ROOT / "production" / "publish.py"]
missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
report = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "production_generator_connected": not missing,
    "automatic_forecast_refresh_enabled": False,
    "missing_components": missing,
    "next_step": "Implement and backtest production generation, player validation, and archival publishing",
}
print(json.dumps(report, indent=2))
# This is an inventory command; it never touches published files.
