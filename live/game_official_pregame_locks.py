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

def main():
    now=datetime.now(timezone.utc)
    observations=json.loads(SOURCE.read_text()).get("records",[])
    old=json.loads(OUT.read_text()).get("records",[]) if OUT.exists() else []
    records=select(observations,old,now)
    # Independently freeze live scoring forecasts when verified DK game odds
    # are missing or stale. This is NOT an official DK-backed lock.
    live_path=ROOT/"live-v2.json"
    if live_path.exists():
        live=json.loads(live_path.read_text())
        generated=dt(live.get("generated_at_utc"))
        already={str(r.get("game_id")) for r in records}
        for game in live.get("games",[]):
            kickoff=dt(game.get("kickoff_utc"))
            game_id=str(game.get("game_id") or "")
            if (not game_id or game_id in already or not kickoff or not generated
                    or not generated<=now<kickoff
                    or not kickoff-timedelta(minutes=15)<=now):
                continue
            if not all(isinstance(game.get(k),(int,float)) and not isinstance(game.get(k),bool)
                       for k in ("projected_margin_home","projected_total")):
                continue
            records.append({
                "game_id":game_id,"season":game.get("season"),"week":game.get("week"),
                "home":game.get("home"),"away":game.get("away"),
                "kickoff_utc":kickoff.isoformat(),"forecast_at_utc":generated.isoformat(),
                "captured_at_utc":now.isoformat(),
                "lock_cutoff_utc":(kickoff-timedelta(minutes=15)).isoformat(),
                "lock_status":"forecast_only",
                "predicted_winner":game.get("predicted_winner"),
                "projected_margin_home":game["projected_margin_home"],
                "projected_total":game["projected_total"],
                "dk_home_spread":None,"dk_total":None,"dk_at_utc":None,
                "source":"frozen pregame model forecast; no verified T-15 DK quote"
            })
            already.add(game_id)
    records.sort(key=lambda r:(str(r.get("kickoff_utc")),str(r.get("game_id"))))
    OUT.write_text(json.dumps({"schema_version":1,"records":records},indent=2)+"\n")
    print(f"Official game locks: {len(records)} total; {len(records)-len(old)} new")

if __name__=="__main__":
    main()
