"""Decide when each game needs its one-hour pregame refresh and final lock.

No API calls are made by this module. The paid refresh opens 60 minutes before
kickoff and stays available until 5 minutes before kickoff if it has not
succeeded yet, because GitHub can delay or drop scheduled ticks. The final
lock is taken at T-30, using the saved forecast and DraftKings observations.
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from live.game_pregame_observations import dt

MARKER=Path("data/dk-slate-refreshes.json")
GAMES=Path("data/live-v2.json")
ACTIVE_WINDOW=timedelta(minutes=60)
LOCK_LEAD=timedelta(minutes=30)
REFRESH_LATE=timedelta(minutes=5)
QUOTE_MAX_AGE=timedelta(minutes=50)
LOCK_TOLERANCE=timedelta(seconds=45)
EVENING_CLEARANCE=timedelta(hours=36)

def slates(games):
    starts=sorted({dt(g.get("kickoff_utc")) for g in games if dt(g.get("kickoff_utc"))})
    return starts

def due_refresh(games, done, now):
    # Refresh each kickoff about an hour ahead. A delayed tick can still run
    # as late as five minutes before kickoff.
    return [k for k in slates(games)
            if REFRESH_LATE <= k-now <= ACTIVE_WINDOW
            and k.isoformat() not in done]

def due_followthrough(games, done, now):
    """Keep the cycle active after the one-hour refresh until T-30 locking."""
    return any(LOCK_LEAD < k-now <= ACTIVE_WINDOW and k.isoformat() in done
               for k in slates(games))

def evening_key(games, done, now):
    """One 7 PM America/Chicago refresh only when no game is that day or soon."""
    local=now.astimezone(ZoneInfo("America/Chicago"))
    key="evening:"+local.date().isoformat()
    if key in done or local.hour != 19 or local.minute >= 15:
        return None
    upcoming=slates(games)
    if any(k.astimezone(ZoneInfo("America/Chicago")).date()==local.date() for k in upcoming):
        return None
    if any(timedelta(0) < k-now <= EVENING_CLEARANCE for k in upcoming):
        return None
    return key

def due_lock(games, now):
    return any(timedelta(0) < k-now <= LOCK_LEAD for k in slates(games))

def cycle_due(games, done, now):
    return bool(due_refresh(games, done, now) or due_lock(games, now)
                or due_followthrough(games, done, now) or evening_key(games, done, now))

def lock_wait_seconds(games, now, limit=30*60):
    """Keep one run alive to write the T-30 lock if the next tick is delayed."""
    active=[k for k in slates(games) if timedelta(0) < k-now <= ACTIVE_WINDOW]
    if not active or any(k-now <= LOCK_LEAD for k in active):
        return 0
    waits=[(k-LOCK_LEAD-now).total_seconds() for k in active]
    return max(0, min(min(waits), limit))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("refresh","lock","cycle"),default="refresh")
    parser.add_argument("--mark",action="store_true")
    parser.add_argument("--slate-only",action="store_true",help="Skip non-game evening refresh; main forecast owns nightly updates")
    args=parser.parse_args()
    games=json.loads(GAMES.read_text()).get("games",[]) if GAMES.exists() else []
    data=json.loads(MARKER.read_text()) if MARKER.exists() else {"schema_version":1,"slates":[]}
    done=set(data.get("slates",[]))
    now=datetime.now(timezone.utc)
    pending=due_refresh(games,done,now)
    evening=None if args.slate_only else evening_key(games,done,now)
    if args.mark:
        if not pending and not evening:
            raise SystemExit("No due refresh to mark")
        data["slates"]=sorted(done|{k.isoformat() for k in pending}|({evening} if evening else set()))
        MARKER.write_text(json.dumps(data,indent=2)+"\n")
        return
    if args.mode=="cycle":
        eligible=cycle_due(games,done,now)
    elif args.mode=="refresh":
        eligible=bool(pending) or bool(evening)
    else:
        eligible=due_lock(games,now)
    print(f"Pregame {args.mode}: {'due' if eligible else 'not due'}")
    if not eligible:
        raise SystemExit(1)

if __name__=="__main__":
    main()
