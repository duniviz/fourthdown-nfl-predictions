"""Grade archived pregame player yardage forecasts against completed NFL games."""
import json
from datetime import datetime,timezone
from pathlib import Path
import nflreadpy as nfl

def main():
    archive=Path("data/player-history.json")
    rows=json.loads(archive.read_text()).get("players",[])
    seasons=sorted({int(x["game_id"].split("_")[0]) for x in rows if x.get("game_id")})
    actual={}
    for season in seasons:
        schedules=nfl.load_schedules([season]).to_dicts()
        completed={(int(g["week"]),g["home_team"],g["away_team"]):str(g["game_id"]) for g in schedules
            if g.get("game_type")=="REG" and g.get("home_score") is not None and g.get("away_score") is not None}
        for r in nfl.load_player_stats([season],summary_level="week").to_dicts():
            try:
                week=int(r["week"]); team=str(r.get("team") or "");opp=str(r.get("opponent_team") or "")
                game_id=completed.get((week,team,opp)) or completed.get((week,opp,team))
                if game_id:
                    for stat in ("passing_yards","rushing_yards","receiving_yards"):
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
            "dk_line":None,"recommended_side":None,"recommendation_result":"not_available"}
        # Grade only a stored pregame line and an explicit stored recommendation.
        if line is not None and x.get("recommended_side") in ("over","under"):
            line=float(line);side=x["recommended_side"]
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
                        "note":"Bias is active only with 40+ archived forecasts; otherwise reported for monitoring."})
    generated=datetime.now(timezone.utc).isoformat()
    Path("data/player-results.json").write_text(json.dumps({
        "generated_at_utc":generated,
        "note":"Only archived pregame projections; missing player stats and absent DK lines are not graded",
        "rows":out},indent=2)+"\n")
    Path("data/player-calibration.json").write_text(json.dumps({
        "generated_at_utc":generated,
        "method":"Market-level mean residual from archived pregame forecasts; capped at ±5 yards and inactive below 40 samples.",
        "markets":markets},indent=2)+"\n")
    print(f"Graded {len(out)} archived player forecasts; no recommendations inferred")
if __name__=="__main__":main()
