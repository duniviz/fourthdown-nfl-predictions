#!/usr/bin/env python3
"""Run the Monday evening full forecast only when an NFL kickoff is approaching."""
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

now=dt.datetime.now(dt.timezone.utc)
local=now.astimezone(ZoneInfo("America/Chicago"))
if local.weekday()!=0 or local.hour<17 or local.hour>21:
    raise SystemExit(1)
try:
    games=json.loads(Path("data/dk-game-odds.json").read_text()).get("games",[])
except (OSError, ValueError):
    games=[]
for game in games:
    try:
        kickoff=dt.datetime.fromisoformat(str(game["commence_time"]).replace("Z","+00:00"))
        minutes=(kickoff-now).total_seconds()/60
    except (KeyError,ValueError,TypeError):
        continue
    if 25<=minutes<=100:
        print("MNF forecast window",game.get("away"),game.get("home"),round(minutes))
        raise SystemExit(0)
print("No upcoming Monday night kickoff within 25–100 minutes")
raise SystemExit(1)
