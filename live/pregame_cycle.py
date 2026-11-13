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
from tools.projection_change_tracker import main as build_projection_changes

DATA = Path("data")
CENTRAL = ZoneInfo("America/Chicago")
REFRESH_CATEGORIES = ("game_odds", "player_props")
FILES = ("dk-odds","dk-game-odds","dk-opening-odds","dk-game-line-history","dk-line-history",
         "dk-pregame-lines","dk-refresh-ledger","dk-slate-refreshes","sportsgameodds-usage",
         "game-pregame-observations","game-official-pregame-locks","pregame-snapshots","player-history","projection-changes")

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

def category_done(state,key,category):
    return state.get("refreshes",{}).get(key,{}).get(category,{}).get("status")=="request_completed"

def slate_done(state,key):
    return all(category_done(state,key,category) for category in REFRESH_CATEGORIES)

def artifact_time(name,field):
    try:
        return observations.dt(read(name,{}).get(field))
    except (OSError,ValueError,TypeError):
        return None

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
    game_odds=[q for q in read("dk-game-odds",{}).get("games",[])
               if q.get("bookmaker")=="draftkings"]
    def recently_verified(value):
        return bool(value and value<=stamp and stamp-value<=timedelta(minutes=30))
    for g in games:
        if g.get("game_id") not in targets:continue
        match=next((q for q in game_odds if q.get("away")==g["away"] and q.get("home")==g["home"]
                    and observations.dt(q.get("commence_time"))==targets[g["game_id"]]),None)
        if not match or match.get("home_spread") is None or match.get("total") is None:return True
        for field in ("home_spread","total"):
            observed=observations.dt(match.get(field+"_observed_at_utc") or match.get("observed_at_utc") or match.get("updated_at_utc"))
            if not recently_verified(observed):return True
    return any(market(p.get("market_key")) in STATS and p.get("game_id") in targets and
               (not (quote:=index.find(p,targets[p["game_id"]])) or not recently_verified(quote[0]))
               for src in ("player-research","count-projections") for p in read(src,{}).get("players",[]))

def refresh(keys,games,stamp):
    state=read("dk-slate-refreshes",{"slates":[]})
    ledger=read("dk-refresh-ledger",{"refreshes":[]})
    month=stamp.astimezone(CENTRAL).strftime("%Y-%m")
    # A slate is complete only after BOTH market families were attempted
    # successfully. Persist each category separately so a failed game-odds
    # request cannot be hidden by successful player props (or vice versa).
    progress=state.setdefault("refreshes",{})
    for key in keys:
        progress.setdefault(key,{})

    def run_primary(category,cmd,artifact):
        if all(category_done(state,key,category) for key in keys):
            return
        entries=[t for t in ledger.get("refreshes",[]) if t.startswith(month)]
        if len(entries)>=125:
            print(f"::warning::Primary request budget exhausted before {category}; slate remains incomplete")
            return
        entries.append(now().astimezone(CENTRAL).isoformat())
        ledger["refreshes"]=entries
        save("dk-refresh-ledger",ledger)
        # Reserve the credit before making the provider request, then commit
        # the reservation to prevent duplicate spends after a runner restart.
        publish("Reserve pregame odds request")
        prior_artifact=artifact_time(*artifact)
        try:
            result=subprocess.run([sys.executable,*cmd],check=False)
            refreshed_at=artifact_time(*artifact)
            finished_at=now()
            succeeded=(result.returncode==0 and refreshed_at is not None and refreshed_at<=finished_at
                       and (prior_artifact is None or refreshed_at>prior_artifact))
        except OSError as exc:
            print(f"::warning::{category} refresh could not start ({type(exc).__name__})")
            succeeded=False
        if succeeded:
            for key in keys:
                progress[key][category]={"status":"request_completed","at_utc":now().isoformat()}
            save("dk-slate-refreshes",state)
            publish(f"Save pregame {category} refresh")
        else:
            print(f"::warning::{category} primary refresh failed or produced no new verified artifact; it will retry before kickoff")

    run_primary("game_odds",["-m","live.dk_game_refresh"],("dk-game-odds","snapshot_date_utc"))
    run_primary("player_props",["-m","tools.refresh_parlayapi_odds","--props-only"],("dk-odds","generated_at_utc"))
    if backup_needed(games,keys,now()):
        try:
            subprocess.run([sys.executable,"-m","tools.refresh_sportsgameodds_backup"],check=True)
        except (OSError,subprocess.CalledProcessError) as exc:
            print(f"::warning::SportsGameOdds backup unavailable ({type(exc).__name__}); preserving verified data")
    line_history.main()
    odds=read("dk-game-odds",{})
    history=read("dk-game-line-history",{"games":{}})
    for row in odds.get("games",[]):
        kickoff=observations.dt(row.get("commence_time"))
        if not kickoff or now()>=kickoff or row.get("bookmaker")!="draftkings":continue
        market_times=[observations.dt(row.get(field+"_observed_at_utc") or row.get("observed_at_utc") or
                                      row.get(field+"_last_verified_at_utc") or row.get("updated_at_utc"))
                      for field in ("home_spread","total") if row.get(field) is not None]
        if not market_times or any(value is None for value in market_times):continue
        captured=min(market_times)
        if captured>=kickoff:continue
        key="|".join((row["away"],row["home"],row["commence_time"]))
        entry={"captured_at_utc":captured.isoformat(),"home_spread":row.get("home_spread"),"total":row.get("total"),
               "home_spread_last_verified_at_utc":row.get("home_spread_last_verified_at_utc") or row.get("updated_at_utc"),
               "total_last_verified_at_utc":row.get("total_last_verified_at_utc") or row.get("updated_at_utc"),
               "source_provider":row.get("source_provider")}
        records=history["games"].setdefault(key,[])
        last_capture=observations.dt(records[-1].get("captured_at_utc")) if records else None
        if not last_capture or captured>last_capture:
            records.append(entry)
    save("dk-game-line-history",history)
    for key in keys:
        if slate_done(state,key):
            state["slates"]=sorted(set(state.get("slates",[]))|{key})
    save("dk-slate-refreshes",state)

def checkpoint(games):
    stamp=now()
    if any(k>stamp for k in slates(games)):
        collect(DATA,stamp)
        stored=read("dk-pregame-lines",{"rows":[]})
        rows=archive(stored["rows"],read("dk-odds",{}),stamp)
        if rows!=stored["rows"]:save("dk-pregame-lines",{**stored,"rows":rows})
        observations.main()
        locks.main()
    build_projection_changes(DATA,stamp)
    publish("Save pregame scoring, player projections and verified DK observations")

def next_wake(games,done,stamp):
    times={k-timedelta(minutes=n) for k in slates(games) for n in (30,15) if n!=30 or k.isoformat() not in done}
    return min((t for t in times if stamp<t<=stamp+timedelta(hours=4)),default=None)

def main():
    subprocess.run(["git","pull","--ff-only","origin","main"],check=True)
    games=read("live-v2")["games"]
    if not games:raise ValueError("Published schedule has no games")
    stamp=now()
    refresh_state=read("dk-slate-refreshes",{"slates":[]})
    done=set(refresh_state.get("slates",[]))
    # Older marker files recorded a slate before the requests completed.
    # Reopen only those legacy markers while they are still in the safe
    # refresh window; historical markers remain untouched.
    for kickoff in due_refresh(games,set(),stamp):
        key=kickoff.isoformat()
        if key in done and not slate_done(refresh_state,key):
            done.discard(key)
    keys=slots(games,done,stamp)
    lock_due=due_lock(games,stamp)
    if not keys and not lock_due:
        print("No pregame refresh or official-lock window is due")
        return

    if keys:
        # Persist available inputs before any provider request can fail.
        checkpoint(games)
        refresh(keys,games,stamp)
        # Reload completion markers in case the provider refresh failed.
        done=set(read("dk-slate-refreshes",{"slates":[]}).get("slates",[]))
    # This scheduled run is intentionally short. The next cron run checks
    # again, so the shared writer queue is released between kickoff windows.
    checkpoint(games)
if __name__=="__main__":main()
