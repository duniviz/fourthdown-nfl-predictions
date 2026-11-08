"""Freeze one official game forecast and DK quote from pre-kickoff observations.

A qualifying pair must be observed within 90 minutes before the 15-minute
pregame cutoff. Freeze on the first available scheduled run at/after T-15
but strictly before kickoff. Never use post-cutoff observations.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from live.game_pregame_observations import dt

ROOT=Path("data")
SOURCE=ROOT/"game-pregame-observations.json"
OUT=ROOT/"game-official-pregame-locks.json"

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

def freeze(live, observations, old, now):
    # Save an early checkpoint even if every near-kickoff runner is delayed.
    # Only a pre-kickoff run can replace a checkpoint with the T-15 selection.
    indexed={r["game_id"]:r for r in old}
    final=[r for r in old if r.get("lock_status")!="early_pregame"]
    for r in select(observations,final,now):
        indexed[r["game_id"]]=r
    stamp=dt(live.get("generated_at_utc"))
    for g in live.get("games",[]):
        gid=g["game_id"]
        kickoff=dt(g.get("kickoff_utc"))
        if not stamp or not kickoff or not stamp<=now<kickoff:continue
        old_row=indexed.get(gid)
        if old_row and dt(old_row.get("kickoff_utc"))!=kickoff:
            previous_kickoff=dt(old_row.get("kickoff_utc"))
            if not previous_kickoff or now>=previous_kickoff:continue
            old_row=None
        if old_row and old_row.get("lock_status")!="early_pregame":continue
        if not all(isinstance(g.get(k),(int,float)) and not isinstance(g[k],bool)
                   for k in ("projected_total","projected_margin_home")):continue
        cutoff=kickoff-timedelta(minutes=15)
        best=max((r for r in observations if r.get("game_id")==gid and dt(r["kickoff_utc"])==kickoff
                  and dt(r["captured_at_utc"])<=min(cutoff,now)),key=lambda r:dt(r["captured_at_utc"]),default=None)
        status="early_pregame" if now<cutoff else "last_available" if best else "forecast_only"
        row={k:g.get(k) for k in ("game_id","season","week","home","away","predicted_winner","projected_home_score",
             "projected_away_score","projected_margin_home","projected_total")}
        row.update(kickoff_utc=kickoff.isoformat(),forecast_at_utc=stamp.isoformat(),dk_total=None,dk_home_spread=None,dk_at_utc=None)
        if best:
            row.update({k:best.get(k) for k in ("dk_total","dk_home_spread","dk_at_utc")})
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
