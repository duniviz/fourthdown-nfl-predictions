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
from live.pregame_capture_guard import LOCK_LEAD, cycle_due, due_refresh, evening_key, lock_wait_seconds, slates
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
    evening=evening_key(games, done, stamp)
    if evening:
        due.append(evening)
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

def fresh_dk_totals(games, keys, stamp):
    """Require a real DraftKings total quote captured within an hour of kickoff."""
    targets={key for key in keys if not key.startswith("evening:")}
    if not targets:
        return True
    odds=read("dk-game-odds",{}).get("games",[])
    for kickoff_key in targets:
        kickoff=observations.dt(kickoff_key)
        if not kickoff:
            return False
        game=next((g for g in games if observations.dt(g.get("kickoff_utc"))==kickoff),None)
        if not game:
            return False
        match=next((row for row in odds if row.get("bookmaker")=="draftkings"
                    and row.get("away")==game.get("away") and row.get("home")==game.get("home")
                    and observations.dt(row.get("commence_time"))==kickoff
                    and row.get("total") is not None),None)
        if not match:
            return False
        observed=observations.dt(match.get("total_observed_at_utc") or match.get("observed_at_utc")
                                 or match.get("total_last_verified_at_utc") or match.get("updated_at_utc"))
        if not observed or not kickoff-timedelta(hours=1)<=observed<=stamp:
            return False
    return True


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

    attempted=False

    def run_primary(category,cmd,artifact):
        nonlocal attempted
        if all(category_done(state,key,category) for key in keys):
            return
        if category=="game_odds" and fresh_dk_totals(games,keys,now()):
            for key in keys:
                progress[key][category]={"status":"request_completed","at_utc":now().isoformat(),
                                         "attempts":progress.get(key,{}).get(category,{}).get("attempts",[]),
                                         "verified_from_existing_quote":True}
            save("dk-slate-refreshes",state)
            publish("Confirm fresh DraftKings totals for pregame slate")
            return
        prior_attempts=max((progress.get(key,{}).get(category,{}).get("attempts",[]) for key in keys),
                           key=len,default=[])
        last_attempt=observations.dt(prior_attempts[-1]) if prior_attempts else None
        if len(prior_attempts)>=2:
            print(f"::warning::{category} reached its two-attempt limit for this kickoff; preserving available data")
            return
        if last_attempt and now()-last_attempt<timedelta(minutes=10):
            print(f"{category} retry is cooling down; it will be checked again in ten minutes")
            return
        entries=[t for t in ledger.get("refreshes",[]) if t.startswith(month)]
        if len(entries)>=125:
            print(f"::warning::Primary request budget exhausted before {category}; slate remains incomplete")
            return
        attempted=True
        attempt_at=now().isoformat()
        for key in keys:
            previous=progress[key].get(category,{})
            progress[key][category]={"status":"pending","attempts":[*previous.get("attempts",[]),attempt_at]}
        entries.append(now().astimezone(CENTRAL).isoformat())
        ledger["refreshes"]=entries
        save("dk-refresh-ledger",ledger)
        # Persist the attempt before spending a provider request, so retries survive runner restarts.
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
        if succeeded and category=="game_odds" and not fresh_dk_totals(games,keys,finished_at):
            print("::warning::DraftKings refreshed, but one or more kickoff groups still lack a current total line; one retry remains")
            succeeded=False
        if succeeded:
            for key in keys:
                progress[key][category]={"status":"request_completed","at_utc":now().isoformat(),
                                         "attempts":progress[key][category].get("attempts",[])}
            save("dk-slate-refreshes",state)
            publish(f"Save pregame {category} refresh")
        else:
            print(f"::warning::{category} refresh failed verification; saved data will be retried once after ten minutes")
    run_primary("game_odds",["-m","live.dk_game_refresh"],("dk-game-odds","snapshot_date_utc"))
    run_primary("player_props",["-m","tools.refresh_parlayapi_odds","--props-only"],("dk-odds","generated_at_utc"))
    if attempted and backup_needed(games,keys,now()):
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

def validate_due_locks(games, stamp):
    saved=read("game-official-pregame-locks",{}).get("records",[])
    by_game={(str(row.get("game_id")),observations.dt(row.get("kickoff_utc"))):row
             for row in saved if isinstance(row,dict)}
    missing=[]
    for game in games:
        kickoff=observations.dt(game.get("kickoff_utc"))
        if not kickoff or not stamp<kickoff or kickoff-stamp>LOCK_LEAD:
            continue
        row=by_game.get((str(game.get("game_id")),kickoff))
        forecast=observations.dt(row.get("forecast_at_utc")) if row else None
        dk_at=observations.dt(row.get("dk_at_utc")) if row else None
        # Same two-hour forecast window the lock writer uses. DK totals stay on one hour.
        fresh_forecast=bool(forecast and kickoff-timedelta(hours=2)<=forecast<=stamp and forecast<kickoff)
        fresh_total=bool(row and row.get("dk_total") is not None and dk_at
                         and kickoff-timedelta(hours=1)<=dk_at<=stamp and dk_at<kickoff)
        if (not row or row.get("lock_status") not in locks.FINAL_STATUSES
                or not fresh_forecast or not fresh_total):
            missing.append(f"{game.get('away')} @ {game.get('home')} ({game.get('game_id')})"
                           f" [forecast fresh={fresh_forecast}, DK total fresh={fresh_total}]")
    if missing:
        raise RuntimeError("Pregame save incomplete: no fresh final lock by T-30 for "+", ".join(missing))
    if any(row.get("lock_status")=="forecast_only" for row in saved):
        print("::warning::One or more forecasts were saved without current DraftKings lines; missing odds remain blank.")

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
    validate_due_locks(games,now())

def next_wake(games,done,stamp):
    times={k-LOCK_LEAD for k in slates(games) if stamp<k-LOCK_LEAD<=stamp+timedelta(hours=4)}
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
    if not cycle_due(games, done, stamp):
        print("No pregame refresh or official-lock window is due")
        return
    keys=slots(games,done,stamp)
    if keys:
        # Fetch the window's lines before writing the lock, so a T-15 snapshot
        # cannot freeze the quote this run is about to replace.
        refresh(keys,games,stamp)
    wait=lock_wait_seconds(games, now())
    if wait:
        print(f"Waiting {int(wait)}s until the T-15 lock for the active kickoff")
        time.sleep(wait)
    checkpoint(games)
if __name__=="__main__":main()
