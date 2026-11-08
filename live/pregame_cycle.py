"""Single writer for kickoff checkpoints, the DK refresh budget, and official locks."""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from live import game_official_pregame_locks as locks, game_pregame_observations as observations
from live import line_history
from live.dk_archive import archive
from live.dk_identity import QuoteIndex, market
from live.pregame_capture_guard import due_refresh, slates
from scripts.capture_pregame_snapshots import collect, STATS

DATA = Path("data")
CENTRAL = ZoneInfo("America/Chicago")
FILES = ("dk-odds","dk-game-odds","dk-opening-odds","dk-game-line-history","dk-line-history",
         "dk-pregame-lines","dk-refresh-ledger","dk-slate-refreshes","sportsgameodds-usage",
         "game-pregame-observations","game-official-pregame-locks","pregame-snapshots","player-history")

def read(name, default=None):
    path=DATA/(name+".json")
    if not path.exists() and default is not None:return default
    return json.loads(path.read_text())

def save(name, data):
    (DATA/(name+".json")).write_text(json.dumps(data,indent=2)+"\n")

def publish(message):
    subprocess.run(["bash","scripts/publish_data.sh",message,*[str(DATA/(f+".json")) for f in FILES]],check=True)

def now():
    return datetime.now(timezone.utc)

def slots(games, done, stamp):
    due=[k.isoformat() for k in due_refresh(games,done,stamp)]
    local=stamp.astimezone(CENTRAL)
    night="evening:"+str(local.date())
    if (games and local.hour==19 and night not in done and
            all(k.astimezone(CENTRAL).date()!=local.date() for k in slates(games))):
        due.append(night)
    return due

def backup_needed(games, keys, stamp):
    odds=read("dk-odds",{})
    index=QuoteIndex(odds.get("rows",[]) if odds.get("bookmaker")=="draftkings" else [],stamp)
    targets={g["game_id"]:observations.dt(g["kickoff_utc"]) for g in games if observations.dt(g["kickoff_utc"])>stamp
             and (any(k.startswith("evening:") for k in keys) or observations.dt(g["kickoff_utc"]).isoformat() in keys)}
    game_odds={(q.get("away"),q.get("home"),observations.dt(q.get("commence_time"))) for q in read("dk-game-odds",{}).get("games",[])
               if q.get("bookmaker")=="draftkings" and q.get("total") is not None and q.get("home_spread") is not None}
    if any((g["away"],g["home"],targets[g["game_id"]]) not in game_odds for g in games if g["game_id"] in targets):
        return True
    return any(market(p.get("market_key")) in STATS and p.get("game_id") in targets and not index.find(p,targets[p["game_id"]])
               for src in ("player-research","count-projections") for p in read(src,{}).get("players",[]))

def refresh(keys,games,stamp):
    state=read("dk-slate-refreshes",{"slates":[]})
    ledger=read("dk-refresh-ledger",{"refreshes":[]})
    month=stamp.astimezone(CENTRAL).strftime("%Y-%m")
    entries=[t for t in ledger["refreshes"] if t.startswith(month)]
    # Reserve two primary requests durably before contacting either endpoint.
    if len(entries)+2>125:
        print("::warning::Primary request budget exhausted; using saved odds")
    else:
        entries.extend([stamp.astimezone(CENTRAL).isoformat()]*2)
        save("dk-refresh-ledger",{"refreshes":entries})
    allowed=len(ledger["refreshes"])==0 or len([t for t in ledger["refreshes"] if t.startswith(month)])+2<=125
    state["slates"]=sorted(set(state["slates"])|set(keys))
    save("dk-slate-refreshes",state)
    publish("Reserve pregame refresh slot")
    if allowed:
        for cmd in (["-m","live.dk_game_refresh"],["-m","tools.refresh_parlayapi_odds","--props-only"]):
            if subprocess.run([sys.executable,*cmd]).returncode:print("::warning::Primary endpoint failed; retaining saved markets")
    if backup_needed(games,keys,now()):
        subprocess.run([sys.executable,"-m","tools.refresh_sportsgameodds_backup"],check=True)
    line_history.main()

def checkpoint(games):
    stamp=now()
    if any(k>stamp for k in slates(games)):
        collect(DATA,stamp)
        stored=read("dk-pregame-lines",{"rows":[]})
        rows=archive(stored["rows"],read("dk-odds",{}),stamp)
        if rows!=stored["rows"]:save("dk-pregame-lines",{**stored,"rows":rows})
        observations.main()
        locks.main()
    publish("Save pregame scoring, player projections and verified DK observations")

def next_wake(games,done,stamp):
    times={k-timedelta(minutes=n) for k in slates(games) for n in (30,15) if n!=30 or k.isoformat() not in done}
    return min((t for t in times if stamp<t<=stamp+timedelta(hours=4)),default=None)

def main():
    deadline=now()+timedelta(hours=5,minutes=25)
    while True:
        subprocess.run(["git","pull","--ff-only","origin","main"],check=True)
        games=read("live-v2")["games"]
        if not games:raise ValueError("Published schedule has no games")
        done=set(read("dk-slate-refreshes",{"slates":[]})["slates"])
        stamp=now()
        keys=slots(games,done,stamp)
        if keys:
            # Persist available inputs before any provider request can fail.
            checkpoint(games)
            refresh(keys,games,stamp)
            done.update(keys)
        checkpoint(games)
        # If a boundary passed while publishing, process it immediately.
        wake=next_wake(games,done,stamp)
        if not wake or wake>=deadline:break
        print("Next capture:",wake.astimezone(CENTRAL).isoformat(),flush=True)
        time.sleep(max(0,(wake-now()).total_seconds()))
if __name__=="__main__":main()
