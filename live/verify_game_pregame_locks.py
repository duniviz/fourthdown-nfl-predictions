"""Fail the capture job if a recently kicked-off game lacks a verified official lock."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from live.game_pregame_observations import dt

DATA=Path("data")

def missing_locks(games,locks,now):
    locked={str(r.get("game_id")) for r in locks if r.get("lock_status")=="official"}
    missing=[]
    for game in games:
        kickoff=dt(game.get("kickoff_utc"))
        if kickoff and kickoff<=now<kickoff+timedelta(minutes=150):
            game_id=str(game.get("game_id"))
            if game_id and game_id not in locked:
                missing.append(game_id)
    return missing

def main():
    now=datetime.now(timezone.utc)
    live=json.loads((DATA/"live-v2.json").read_text())
    locks=json.loads((DATA/"game-official-pregame-locks.json").read_text()).get("records",[])
    missing=missing_locks(live.get("games",[]),locks,now)
    if missing:
        raise SystemExit("MISSING OFFICIAL PREGAME LOCK (no post-cutoff backfill permitted): "+", ".join(missing))
    print("Official pregame lock verification passed for recently kicked-off games")

if __name__=="__main__":
    main()
