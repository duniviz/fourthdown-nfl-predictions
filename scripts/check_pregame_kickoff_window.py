#!/usr/bin/env python3
"""Exit 0 only when a known NFL game is 5–25 minutes from kickoff."""
import datetime as dt
import json
import pathlib
import sys
path=pathlib.Path("data/dk-game-odds.json")
try:
    games=json.loads(path.read_text()).get("games",[])
except (OSError,ValueError):
    games=[]
now=dt.datetime.now(dt.timezone.utc)
for game in games:
    try:
        kickoff=dt.datetime.fromisoformat(str(game["commence_time"]).replace("Z","+00:00"))
        remaining=(kickoff-now).total_seconds()/60
    except (ValueError,TypeError,KeyError):
        continue
    if 5<=remaining<=25:
        print("PREGAME_WINDOW",game.get("away"),game.get("home"),round(remaining,1))
        sys.exit(0)
print("No kickoff within 5–25 minutes")
sys.exit(1)
