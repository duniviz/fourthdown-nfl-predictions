"""Grade archived pregame player yardage forecasts against completed NFL games."""
import json
import time
from datetime import datetime,timezone
from pathlib import Path
import nflreadpy as nfl
from live.player_research import METRICS

def main():
    archive=Path("data/player-history.json")
    observations=json.loads(archive.read_text()).get("players",[])
    # Historical observations remain append-only, but each player/game/market
    # contributes exactly one closest eligible pre-kickoff record to grading.
    # Never select a quote or forecast captured after kickoff.
    def parsed(value):
        try:
            d=datetime.fromisoformat(str(value).replace("Z","+00:00"))
            return d.astimezone(timezone.utc) if d.tzinfo else None
        except (ValueError,TypeError):
            return None

    latest={}
    for row in observations:
        kickoff=parsed(row.get("kickoff_utc") or row.get("kickoff"))
        forecast=parsed(row.get("forecast_captured_at_utc") or row.get("captured_at"))
        quote=parsed(row.get("dk_quote_time") or row.get("dk_captured_at"))
        if not kickoff or not forecast or not forecast<kickoff:
            continue
        if row.get("dk_line") is not None and (not quote or not quote<kickoff):
            continue
        key=(str(row.get("game_id")),str(row.get("player_id")),str(row.get("stat_key")))
        if not all(key) or "None" in key:
            continue
        candidate=(forecast,quote or forecast)
        if key not in latest or candidate>latest[key][0]:
            latest[key]=(candidate,row)
    rows=[entry[1] for entry in latest.values()]
    print(f"Selected {len(rows)} official pregame snapshots from {len(observations)} observations")
    seasons=sorted({int(x["game_id"].split("_")[0]) for x in rows if x.get("game_id")})
    actual={}
    for season in seasons:
        for attempt in range(3):
            try:
                schedules=nfl.load_schedules([season]).to_dicts()
                stats=nfl.load_player_stats([season],summary_level="week").to_dicts()
                break
            except (ConnectionError, TimeoutError, OSError) as exc:
                if attempt == 2:
                    print(f"WARNING: nflverse download failed for {season}; preserving existing player grading: {exc}")
                    return
                time.sleep(2 ** attempt)
        completed={(int(g["week"]),g["home_team"],g["away_team"]):str(g["game_id"]) for g in schedules
            if g.get("game_type")=="REG" and g.get("home_score") is not None and g.get("away_score") is not None}
        for r in stats:
            try:
                week=int(r["week"]); team=str(r.get("team") or "");opp=str(r.get("opponent_team") or "")
                game_id=completed.get((week,team,opp)) or completed.get((week,opp,team))
                if game_id:
                    for stat, _, _ in METRICS:
                        val=r.get(stat)
                        if val is not None:
                            actual[(game_id,str(r.get("player_id")),stat)]=float(val)
            except (TypeError,ValueError,KeyError):continue
    out=[]
    for x in rows:
        key=(str(x.get("game_id")),str(x.get("player_id")),str(x.get("stat_key")))
        if key not in actual:continue
        proj=float(x["projection"]); observed=actual[key]
        line=x.get("dk_line")
        result={"game_id":key[0],"player_id":key[1],"player":x.get("player"),
            "team":x.get("team"),"market":x.get("market"),"stat_key":key[2],
            "projection":proj,"actual":observed,"error":round(observed-proj,1),
            "dk_line":float(line) if line is not None and str(line).strip() and float(line)>0 else None,"recommended_side":None,"recommendation_result":"not_available"}
        # Grade only a stored pregame line and an explicit stored recommendation.
        if result["dk_line"] is not None and str(x.get("recommended_side") or "").strip().lower() in ("over","under"):
            line=float(line);side=str(x["recommended_side"]).strip().lower()
            result["dk_line"]=line;result["recommended_side"]=side
            result["recommendation_result"]="push" if observed==line else (
                "hit" if (observed>line)==(side=="over") else "miss")
        out.append(result)
    # Market-level bias is learned only from saved forecasts. It feeds the next
    # run and is applied by player_research only after a minimum sample is met.
    grouped={}
    for row in out:
        key=row["stat_key"]
        grouped.setdefault(key,[]).append(float(row["error"]))
    markets=[]
    for key,errors in sorted(grouped.items()):
        n=len(errors)
        mae=sum(abs(v) for v in errors)/n
        mean=sum(errors)/n
        markets.append({"stat_key":key,"sample_size":n,"mean_error":round(mean,2),
                        "mae":round(mae,2),"active":n>=40,
                        "probability_calibrated":False,
                        "note":"Residual bias is tracked after 40 forecasts. Probability calibration for betting recommendations is not established by residual MAE alone."})
    generated=datetime.now(timezone.utc).isoformat()
    Path("data/player-results.json").write_text(json.dumps({
        "generated_at_utc":generated,
        "note":"Only archived pregame projections; missing player stats and absent DK lines are not graded",
        "rows":out},indent=2)+"\n")
    Path("data/player-calibration.json").write_text(json.dumps({
        "generated_at_utc":generated,
        "method":"Market-level mean residual from archived pregame forecasts. This is not probability calibration; recommendation probability gates remain off until separately validated.",
        "markets":markets},indent=2)+"\n")
    print(f"Graded {len(out)} archived player forecasts; no recommendations inferred")
if __name__=="__main__":main()
