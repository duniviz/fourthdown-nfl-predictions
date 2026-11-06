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

# One evening refresh at 7 PM America/Chicago on days without NFL kickoffs.
# The separate capture-game-pregame workflow handles game-day kickoff slates.
def has_game_today():
    try:
        payload = json.loads(pathlib.Path("data/live-v2.json").read_text())
        games = payload["games"]
        if not isinstance(games, list) or not games:
            return None
        for game in games:
            kickoff = dt.datetime.fromisoformat(str(game["kickoff_utc"]).replace("Z", "+00:00"))
            if kickoff.astimezone(ZoneInfo("America/Chicago")).date() == local.date():
                return True
        return False
    except (OSError, ValueError, TypeError, KeyError):
        return None

if "--refresh" in sys.argv:
    if len(month_entries()) >= limit:
        print("MONTHLY_REFRESH_CAP_REACHED", limit)
        sys.exit(1)
    if "--force" in sys.argv:
        print("MANUAL_REFRESH", local.isoformat(), len(month_entries()) + 1, "of", limit)
        sys.exit(0)
    game_today = has_game_today()
    if local.hour == 19 and local.minute < 15 and game_today is False:
        print("NO_GAME_EVENING_REFRESH", local.isoformat(), len(month_entries()) + 1, "of", limit)
        sys.exit(0)
    print("Skipping refresh: outside 7 PM Central no-game window, game scheduled, or schedule unavailable")

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
