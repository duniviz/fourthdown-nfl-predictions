#!/usr/bin/env python3
"""Central-time DK refresh slots with a hard 125-request monthly budget."""
import datetime as dt
import json
import pathlib
import sys
from zoneinfo import ZoneInfo

UTC = dt.timezone.utc
now = dt.datetime.now(UTC)
local = now.astimezone(ZoneInfo("America/Chicago"))
ledger = pathlib.Path("data/dk-refresh-ledger.json")
limit = 125

def entries():
    try:
        value = json.loads(ledger.read_text()).get("refreshes", [])
        return [x for x in value if isinstance(x, str)]
    except (OSError, ValueError, TypeError):
        return []

def month_entries():
    month = local.strftime("%Y-%m")
    return [x for x in entries() if x.startswith(month)]

if "--record" in sys.argv:
    rows = month_entries()
    rows.append(local.isoformat())
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps({"refreshes": rows}, indent=2) + "\n")
    print("RECORDED_REFRESH", len(rows), "of", limit)
    sys.exit(0)

# Tuesday 2, Wednesday 2, Thursday 5, Friday 1,
# Saturday 3, Sunday 13, Monday 5 = 31 per week.
# All times are America/Chicago. The cap protects 5-week months.
slots = {
    0: (10, 14, 17, 18, 19),
    1: (9, 17),
    2: (9, 17),
    3: (10, 14, 17, 18, 19),
    4: (16,),
    5: (9, 14, 19),
    6: tuple(range(8, 21)),
}
if "--refresh" in sys.argv:
    if len(month_entries()) >= limit:
        print("MONTHLY_REFRESH_CAP_REACHED", limit)
        sys.exit(1)
    if "--force" in sys.argv:
        print("MANUAL_REFRESH", local.isoformat(), len(month_entries()) + 1, "of", limit)
        sys.exit(0)
    if local.hour in slots[local.weekday()] and local.minute < 10:
        print("SCHEDULED_REFRESH", local.isoformat(), len(month_entries()) + 1, "of", limit)
        sys.exit(0)
    print("Outside scheduled refresh slot")
    sys.exit(1)

# Preserve the independent final pregame snapshot trigger at 30 minutes.
try:
    games = json.loads(pathlib.Path("data/dk-game-odds.json").read_text()).get("games", [])
except (OSError, ValueError):
    games = []
for game in games:
    try:
        kickoff = dt.datetime.fromisoformat(str(game["commence_time"]).replace("Z", "+00:00"))
        remaining = (kickoff - now).total_seconds() / 60
    except (ValueError, TypeError, KeyError):
        continue
    if 25 <= remaining <= 35:
        print("PREGAME_WINDOW", game.get("away"), game.get("home"), round(remaining, 1))
        sys.exit(0)
print("No pregame snapshot window")
sys.exit(1)
