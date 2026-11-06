"""Decide whether to fetch odds once per kickoff slate, or check T-15 locks.

No API calls are made by this module. Refresh marker is committed only after
a successful provider refresh and observation capture.
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from live.game_pregame_observations import dt

MARKER=Path("data/dk-slate-refreshes.json")
GAMES=Path("data/live-v2.json")

def slates(games):
    starts=sorted({dt(g.get("kickoff_utc")) for g in games if dt(g.get("kickoff_utc"))})
    return starts

def due_refresh(games, done, now):
    # Allow the next scheduled run up to 10 minutes late, never refresh after
    # the T-15 freeze window begins.
    return [k for k in slates(games)
            if timedelta(minutes=20) <= k-now <= timedelta(minutes=30)
            and k.isoformat() not in done]

def evening_key(games, done, now):
    """One 7 PM America/Chicago refresh only when no game kicks off that day."""
    local=now.astimezone(ZoneInfo("America/Chicago"))
    key="evening:"+local.date().isoformat()
    if key in done or local.hour != 19 or local.minute >= 15:
        return None
    if any(k.astimezone(ZoneInfo("America/Chicago")).date()==local.date() for k in slates(games)):
        return None
    return key

def due_lock(games, now):
    return any(timedelta(0)<k-now<=timedelta(minutes=15) for k in slates(games))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("refresh","lock"),default="refresh")
    parser.add_argument("--mark",action="store_true")
    args=parser.parse_args()
    games=json.loads(GAMES.read_text()).get("games",[]) if GAMES.exists() else []
    data=json.loads(MARKER.read_text()) if MARKER.exists() else {"schema_version":1,"slates":[]}
    done=set(data.get("slates",[]))
    now=datetime.now(timezone.utc)
    pending=due_refresh(games,done,now)
    evening=evening_key(games,done,now)
    if args.mark:
        if not pending and not evening:
            raise SystemExit("No due refresh to mark")
        data["slates"]=sorted(done|{k.isoformat() for k in pending}|({evening} if evening else set()))
        MARKER.write_text(json.dumps(data,indent=2)+"\n")
        return
    eligible=(bool(pending) or bool(evening)) if args.mode=="refresh" else due_lock(games,now)
    print(f"Pregame {args.mode}: {'due' if eligible else 'not due'}")
    if not eligible:
        raise SystemExit(1)

if __name__=="__main__":
    main()
