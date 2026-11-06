"""Freeze one official game forecast and DK quote from pre-kickoff observations.

A qualifying pair must be observed in the 90 minutes before the 30-minute
pregame cutoff. Freeze at the first scheduled run from 30 to 15 minutes before kickoff, never
using observations or quote timestamps after the cutoff.
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
        if not kickoff or not forecast or not quote or not captured or not (kickoff-timedelta(minutes=30)<=now<=kickoff-timedelta(minutes=15)):
            continue
        cutoff=kickoff-timedelta(minutes=30)
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
        locked[key]={**row,"lock_cutoff_utc":(dt(row["kickoff_utc"])-timedelta(minutes=30)).isoformat(),
                     "lock_status":"official"}
    return sorted(locked.values(),key=lambda x:(str(x.get("kickoff_utc")),str(x.get("game_id"))))

def main():
    now=datetime.now(timezone.utc)
    observations=json.loads(SOURCE.read_text()).get("records",[])
    old=json.loads(OUT.read_text()).get("records",[]) if OUT.exists() else []
    records=select(observations,old,now)
    OUT.write_text(json.dumps({"schema_version":1,"records":records},indent=2)+"\n")
    print(f"Official game locks: {len(records)} total; {len(records)-len(old)} new")

if __name__=="__main__":
    main()
