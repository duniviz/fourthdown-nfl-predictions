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
from live.pregame_refresh_state import (reserved_attempt, record_result,
    MONTHLY_PRIMARY_REQUEST_CAP)
from scripts.capture_pregame_snapshots import collect, STATS

DATA = Path("data")
CENTRAL = ZoneInfo("America/Chicago")
FILES = ("dk-odds","dk-game-odds","dk-opening-odds","dk-game-line-history","dk-line-history",
         "dk-pregame-lines","dk-refresh-ledger","dk-slate-refreshes","sportsgameodds-usage",
         "game-pregame-observations","game-official-pregame-locks","pregame-snapshots","player-history")
PRIMARY_COMMANDS = (["-m","live.dk_game_refresh"], ["-m","tools.refresh_parlayapi_odds","--props-only"])

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

def refresh(keys,games,stamp,run=subprocess.run):
    state=read("dk-slate-refreshes",{"slates":[]})
    ledger=read("dk-refresh-ledger",{"refreshes":[]})
    month=stamp.astimezone(CENTRAL).strftime("%Y-%m")
    entries=[t for t in ledger["refreshes"] if t.startswith(month)]
    state, reserved_count, pending, attempt=reserved_attempt(
        state, len(entries), keys, stamp.isoformat())
    if not pending:
        return True
    if attempt in ("budget_exhausted", "attempts_exhausted"):
        print(f"::warning::Primary refresh {attempt}; retaining saved odds and recording failure")
        save("dk-slate-refreshes",state)
        publish("Record pregame odds refresh failure")
        return False
    reserved_at=stamp.astimezone(CENTRAL).isoformat()
    entries=[t for t in ledger["refreshes"] if not t.startswith(month)]
    entries.extend([reserved_at]*reserved_count)
    save("dk-refresh-ledger",{"refreshes":entries})
    save("dk-slate-refreshes",state)
    publish("Reserve pregame refresh slot")
    attempt_number, requested=attempt
    results={}
    for provider,cmd in zip(("game","player"),PRIMARY_COMMANDS):
        if provider in requested:
            results[provider]=run([sys.executable,*cmd]).returncode==0
    primary_ok=all(state.get("provider_success",{}).get(key,{}).get(provider,False) or results.get(provider,False)
                   for key in pending for provider in ("game","player"))
    if not primary_ok: print("::warning::At least one primary odds refresh failed; retaining saved markets and scheduling a bounded retry")
    backup_ok=True
    if backup_needed(games,keys,now()):
        backup_ok=run([sys.executable,"-m","tools.refresh_sportsgameodds_backup"]).returncode==0
        if not backup_ok: print("::warning::Backup odds refresh failed; retaining previously saved quotes")
    line_history.main()
    odds=read("dk-game-odds",{})
    history=read("dk-game-line-history",{"games":{}})
    for row in odds.get("games",[]):
        kickoff=observations.dt(row.get("commence_time"))
        if not kickoff or now()>=kickoff or row.get("bookmaker")!="draftkings":continue
        key="|".join((row["away"],row["home"],row["commence_time"]))
        entry={"captured_at_utc":now().isoformat(),"home_spread":row.get("home_spread"),"total":row.get("total"),
               "home_spread_last_verified_at_utc":row.get("home_spread_last_verified_at_utc") or row.get("updated_at_utc"),
               "total_last_verified_at_utc":row.get("total_last_verified_at_utc") or row.get("updated_at_utc"),
               "source_provider":row.get("source_provider")}
        records=history["games"].setdefault(key,[])
        if not records or any(records[-1].get(field)!=entry[field] for field in ("home_spread","total")):
            records.append(entry)
    save("dk-game-line-history",history)
    state=record_result(state,pending,attempt_number,results,backup_ok)
    save("dk-slate-refreshes",state)
    publish("Record pregame odds refresh result")
    return primary_ok

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
            succeeded=refresh(keys,games,stamp)
            if succeeded: done.update(keys)
        state=read("dk-slate-refreshes",{"slates":[]})
        pending_attempts={k for k in state.get("attempts",{}) if k not in set(state.get("slates",[]))|set(state.get("failed_slates",[]))}
        checkpoint(games)
        # If a boundary passed while publishing, process it immediately.
        wake=next_wake(games,done,stamp)
        if pending_attempts:
            current=now()
            retry_at=current+timedelta(minutes=5)
            cutoffs=[observations.dt(g["kickoff_utc"])-timedelta(minutes=15) for g in games
                     if observations.dt(g.get("kickoff_utc")) and observations.dt(g["kickoff_utc"]).isoformat() in pending_attempts
                     and observations.dt(g["kickoff_utc"])-timedelta(minutes=15)>current]
            if not cutoffs and not any(k.startswith("evening:") for k in pending_attempts):
                state["failed_slates"]=sorted(set(state.get("failed_slates",[]))|pending_attempts)
                state["failures"]={**state.get("failures",{}),**{k:"retry window closed before provider recovery" for k in pending_attempts}}
                save("dk-slate-refreshes",state)
                publish("Record pregame odds retry window failure")
            else:
                if cutoffs: retry_at=min(retry_at,min(cutoffs))
                wake=min(wake,retry_at) if wake else retry_at
        if not wake or wake>=deadline:break
        print("Next capture:",wake.astimezone(CENTRAL).isoformat(),flush=True)
        time.sleep(max(0,(wake-now()).total_seconds()))
if __name__=="__main__":main()
