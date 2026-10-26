"""Independent validation checks for the FOURTHDOWN v2 research baseline."""
import json
from collections import defaultdict
from pathlib import Path
from .rolling import load_rows, _number
from .v2 import build_v2_predictions

def accuracy(rows, predictor):
    valid=[r for r in rows if r["actual_margin"] != 0 and predictor(r) != 0]
    return {"games":len(valid), "accuracy":round(sum((predictor(r)>0)==(r["actual_margin"]>0) for r in valid)/len(valid),4) if valid else None}

def evaluate(schedules, team_games):
    predictions=build_v2_predictions(schedules,team_games)
    by_id={r["game_id"]:r for r in schedules}
    rows=[]
    for p in predictions:
        schedule=by_id[p["game_id"]]
        spread=_number(schedule.get("spread_line"))
        # nflverse spread_line convention: positive number means home favored.
        # Do not interpret this as timestamped pregame odds.
        row={**p,"spread_line":spread}
        rows.append(row)
    out={"v2_winners":accuracy(rows,lambda r:r["pred_margin"]),
         "home_team_baseline":accuracy(rows,lambda r:1.0),
         "market_favorite_baseline":accuracy([r for r in rows if r["spread_line"] is not None and r["spread_line"]!=0],lambda r:r["spread_line"]),
         "segments":{}}
    for label,subset in {
        "home_predictions":[r for r in rows if r["pred_margin"]>0],
        "away_predictions":[r for r in rows if r["pred_margin"]<0],
        "market_home_favorites":[r for r in rows if r["spread_line"] is not None and r["spread_line"]>0],
        "market_away_favorites":[r for r in rows if r["spread_line"] is not None and r["spread_line"]<0],
        "v2_agrees_with_market":[r for r in rows if r["spread_line"] is not None and r["spread_line"]*r["pred_margin"]>0],
        "v2_disagrees_with_market":[r for r in rows if r["spread_line"] is not None and r["spread_line"]*r["pred_margin"]<0],
    }.items():
        out["segments"][label]=accuracy(subset,lambda r:r["pred_margin"])
    out["by_season"]={str(year):{
        "v2":accuracy([r for r in rows if r["season"]==year],lambda r:r["pred_margin"]),
        "home":accuracy([r for r in rows if r["season"]==year],lambda r:1.0),
        "market":accuracy([r for r in rows if r["season"]==year and r["spread_line"] is not None and r["spread_line"]!=0],lambda r:r["spread_line"])
    } for year in sorted({r["season"] for r in rows})}
    # Future-data perturbation: mutate only the latest week and verify all
    # predictions at or before that week remain exactly identical.
    if rows:
        season=max(r["season"] for r in rows)
        week=max(r["week"] for r in rows if r["season"]==season)
        altered=[dict(r) for r in team_games]
        for r in altered:
            if int(r["season"])==season and int(r["week"])==week:
                r["offense_epa"]="999"
                r["defense_epa"]="-999"
        before={(r["season"],r["week"],r["game_id"]):(r["pred_margin"],r["pred_total"]) for r in predictions}
        after={(r["season"],r["week"],r["game_id"]):(r["pred_margin"],r["pred_total"]) for r in build_v2_predictions(schedules,altered)}
        out["future_data_perturbation_passed"]=all(after.get(k)==v for k,v in before.items())
    else:
        out["future_data_perturbation_passed"]=None
    out["notes"]=[
        "Market spread_line may reflect closing odds, not odds available at prediction time.",
        "Market comparison is a benchmark, not a betting ROI or ATS evaluation.",
        "No Elo benchmark or timestamped injury/quarterback features are included yet.",
        "Only same-week and later data perturbation is checked; broader source audits remain necessary."
    ]
    return out

def main():
    folder=Path("data")
    print(json.dumps(evaluate(load_rows(folder/"schedules.csv"),load_rows(folder/"team_epa.csv")),indent=2))

if __name__=="__main__":
    main()
