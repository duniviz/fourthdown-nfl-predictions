"""Freeze one official game forecast and DK quote from pre-kickoff observations.

A qualifying official pair must be observed within 90 minutes before the
15-minute cutoff. Otherwise the active kickoff window saves an early
checkpoint and replaces it, once, with the freshest pre-kickoff quote at
about T-15 (last_available). Games outside that window, and every lock whose
kickoff has already passed, are left unchanged.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from live.game_pregame_observations import dt
from live.pregame_capture_guard import ACTIVE_WINDOW, LOCK_LEAD, LOCK_TOLERANCE, QUOTE_MAX_AGE

ROOT=Path("data")
SOURCE=ROOT/"game-pregame-observations.json"
OUT=ROOT/"game-official-pregame-locks.json"
FINAL_STATUSES=("official","last_available","forecast_only")

def select(records, existing, now):
    locked={str(r["game_id"]):r for r in existing if isinstance(r,dict) and r.get("game_id")}
    grouped={}
    for row in records:
        if not isinstance(row,dict) or not row.get("game_id"):
            continue
        kickoff=dt(row.get("kickoff_utc"))
        forecast=dt(row.get("forecast_at_utc"))
        quote=dt(row.get("dk_at_utc"))
        captured=dt(row.get("captured_at_utc"))
        if not kickoff or not forecast or not quote or not captured or not (kickoff-timedelta(minutes=15)<=now<kickoff):
            continue
        cutoff=kickoff-timedelta(minutes=15)
        earliest=cutoff-timedelta(minutes=90)
        if not (earliest<=forecast<=cutoff and earliest<=quote<=cutoff and captured<=cutoff):
            continue
        if row.get("projected_margin_home") is None or row.get("projected_total") is None:
            continue
        if row.get("dk_home_spread") is None and row.get("dk_total") is None:
            continue
        key=str(row["game_id"])
        if key in locked:
            continue
        rank=(min(forecast,quote),max(forecast,quote))
        if key not in grouped or rank>grouped[key][0]:
            grouped[key]=(rank,row)
    for key,(_,row) in grouped.items():
        locked[key]={**row,"lock_cutoff_utc":(dt(row["kickoff_utc"])-timedelta(minutes=15)).isoformat(),
                     "lock_status":"official"}
    return sorted(locked.values(),key=lambda x:(str(x.get("kickoff_utc")),str(x.get("game_id"))))

def _quote_at(row):
    return dt(row.get("dk_at_utc")) if isinstance(row,dict) else None

def _fresh(quote_at, kickoff):
    return bool(quote_at and kickoff-QUOTE_MAX_AGE <= quote_at < kickoff)

def _best_quote(observations, gid, kickoff, cutoff, now):
    eligible=[]
    for row in observations:
        if not isinstance(row,dict) or row.get("game_id")!=gid or dt(row.get("kickoff_utc"))!=kickoff:
            continue
        captured=dt(row.get("captured_at_utc"))
        quote=_quote_at(row)
        if not captured or not quote or captured>now or captured>=kickoff or quote>=kickoff:
            continue
        eligible.append(row)
    if not eligible:
        return None
    pre=[row for row in eligible if dt(row["captured_at_utc"])<=cutoff and _quote_at(row)<=cutoff]
    pool=pre or (eligible if now+LOCK_TOLERANCE>=cutoff else [])
    return max(pool, key=_quote_at)

def freeze(live, observations, old, now):
    indexed={r["game_id"]:r for r in old if isinstance(r,dict) and r.get("game_id")}
    final=[r for r in old if isinstance(r,dict) and r.get("lock_status")!="early_pregame"]
    for row in select(observations, final, now):
        indexed[row["game_id"]]=row
    stamp=dt(live.get("generated_at_utc"))
    for g in live.get("games",[]):
        gid=g.get("game_id")
        kickoff=dt(g.get("kickoff_utc"))
        if not gid or not stamp or not kickoff or not stamp<=now<kickoff:
            continue
        old_row=indexed.get(gid)
        previous=dt(old_row.get("kickoff_utc")) if isinstance(old_row,dict) else None
        kickoff_changed=bool(previous and previous!=kickoff)
        if kickoff_changed:
            # A moved kickoff can be replaced only while the previous kickoff
            # is still in the future. After that, keep the historical lock.
            if now>=previous:
                continue
            old_row=None
        if not (timedelta(0)<kickoff-now<=ACTIVE_WINDOW or kickoff_changed):
            continue
        if not all(isinstance(g.get(k),(int,float)) and not isinstance(g[k],bool)
                   for k in ("projected_total","projected_margin_home")):
            continue
        cutoff=kickoff-LOCK_LEAD
        best=_best_quote(observations, gid, kickoff, cutoff, now)
        chosen=best
        quote=_quote_at(best)
        old_quote=_quote_at(old_row)
        if old_row and old_quote and old_quote<kickoff and (not quote or old_quote>=quote):
            chosen=old_row
            quote=old_quote
        if old_row and old_row.get("lock_status") in FINAL_STATUSES and not kickoff_changed:
            # A fresh final lock stays put. A stale one can still take a newer
            # pre-kickoff quote. Completed games never reach this loop.
            if _fresh(old_quote, kickoff) or not (quote and (old_quote is None or quote>old_quote)):
                continue
        at_lock=now+LOCK_TOLERANCE>=cutoff
        if not at_lock:
            status="early_pregame"
        elif _fresh(quote, kickoff) or kickoff-now<=timedelta(minutes=5):
            status="last_available" if quote else "forecast_only"
        else:
            status="early_pregame"
        row={k:g.get(k) for k in ("game_id","season","week","home","away","predicted_winner","projected_home_score",
             "projected_away_score","projected_margin_home","projected_total")}
        row.update(kickoff_utc=kickoff.isoformat(),forecast_at_utc=stamp.isoformat(),dk_total=None,dk_home_spread=None,dk_at_utc=None)
        if quote and chosen:
            row.update({k:chosen.get(k) for k in ("dk_total","dk_home_spread","dk_at_utc")})
        row.update(lock_status=status,lock_cutoff_utc=cutoff.isoformat(),captured_at_utc=now.isoformat(),
                   source="published pregame forecast and available verified DK observations")
        if not old_row or any(old_row.get(k)!=v for k,v in row.items() if k!="captured_at_utc"):
            indexed[gid]=row
    return list(indexed.values())

def main():
    now=datetime.now(timezone.utc)
    observations=json.loads(SOURCE.read_text()).get("records",[])
    old=json.loads(OUT.read_text()).get("records",[]) if OUT.exists() else []
    live=json.loads((ROOT/"live-v2.json").read_text())
    records=freeze(live, observations, old, now)
    records.sort(key=lambda r:(str(r.get("kickoff_utc")),str(r.get("game_id"))))
    OUT.write_text(json.dumps({"schema_version":1,"records":records},indent=2)+"\n")
    print(f"Official game locks: {len(records)} total; {len(records)-len(old)} new")

if __name__=="__main__":
    main()
