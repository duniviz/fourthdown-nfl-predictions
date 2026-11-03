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
# 08:00 and 17:00 Central, Tuesday through Saturday.
if refresh and local.weekday() in (1,2,3,4,5) and local.hour in (8,17) and local.minute<10:
    print("DAILY_REFRESH",local.isoformat())
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
    # API refresh at ~60 and ~30 minutes; snapshot only at ~30.
    windows=((55,65),(25,35)) if refresh else ((25,35),)
    if any(low<=remaining<=high for low,high in windows):
        print("PREGAME_WINDOW",game.get("away"),game.get("home"),round(remaining,1))
        sys.exit(0)
print("No scheduled refresh/snapshot window")
sys.exit(1)
