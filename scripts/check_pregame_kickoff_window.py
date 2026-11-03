#!/usr/bin/env python3
"""Kickoff-aware polling gate; use --refresh for API refresh cadence."""
import datetime as dt
import json
import pathlib
import sys
from zoneinfo import ZoneInfo

now=dt.datetime.now(dt.timezone.utc)
local=now.astimezone(ZoneInfo("America/Chicago"))
refresh="--refresh" in sys.argv
# Central-time API cadence: Tue-Fri every 2 hours, Sat-Mon hourly.
# Only the first 10-minute cron tick in each slot runs.
if refresh:
    weekday=local.weekday()
    interval=2 if weekday in (1,2,3,4) else 1
    if local.hour % interval == 0 and local.minute < 10:
        print("SCHEDULED_REFRESH",local.isoformat())
        sys.exit(0)
try:
    games=json.loads(pathlib.Path("data/dk-game-odds.json").read_text()).get("games",[])
except (OSError,ValueError):
    games=[]
for game in games:
    try:
        kickoff=dt.datetime.fromisoformat(str(game["commence_time"]).replace("Z","+00:00"))
        remaining=(kickoff-now).total_seconds()/60
    except (ValueError,TypeError,KeyError):
        continue
    # Keep final snapshot capture at 30 minutes. During the final two
    # hours, refresh the market at each half-hour boundary as well.
    if refresh and 0 < remaining <= 120 and local.minute % 30 < 10:
        print("NEAR_KICKOFF_REFRESH",game.get("away"),game.get("home"),round(remaining,1))
        sys.exit(0)
    windows=((55,65),(25,35)) if refresh else ((25,35),)
    if any(low<=remaining<=high for low,high in windows):
        print("PREGAME_WINDOW",game.get("away"),game.get("home"),round(remaining,1))
        sys.exit(0)
print("No scheduled refresh/snapshot window")
sys.exit(1)
