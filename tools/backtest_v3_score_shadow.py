#!/usr/bin/env python3
"""Leak-free historical V2 vs V3 game-score replay.

2024 is a development period and 2025 is an untouched holdout.  Each team's
pace, success-rate, and pass-play proxy use only completed prior weeks.  This
tool is research-only and never reads or writes live forecast files.
"""
import json
import math
from collections import defaultdict
from pathlib import Path
from backtest.v2 import build_v2_predictions
from v3_score_shadow import PACE_POINTS_PER_PLAY, SUCCESS_MARGIN_POINTS, PASS_MARGIN_POINTS, MAX_TOTAL_ADJUSTMENT, MAX_MARGIN_ADJUSTMENT

def num(value):
    try:
        value=float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None

def metric(errors):
    if not errors:
        return {"samples":0,"mae":None,"rmse":None}
    return {"samples":len(errors),"mae":round(sum(abs(x) for x in errors)/len(errors),3),
            "rmse":round(math.sqrt(sum(x*x for x in errors)/len(errors)),3)}

def weekly_features(pbp, schedules):
    completed={(int(g["season"]),int(g["week"]),str(g["game_id"])) for g in schedules
      if g.get("game_type","REG")=="REG" and num(g.get("home_score")) is not None and num(g.get("away_score")) is not None}
    buckets=defaultdict(lambda: defaultdict(lambda: {"plays":0,"success":[],"pass":0}))
    for row in pbp:
        try:
            season,week,gid=int(row["season"]),int(row["week"]),str(row["game_id"])
            team=row.get("posteam")
            if (season,week,gid) not in completed or not team or row.get("play_type") not in ("pass","run"):
                continue
        except (KeyError,TypeError,ValueError):
            continue
        bucket=buckets[(season,week)][team]
        bucket["plays"]+=1
        if row.get("play_type")=="pass":
            bucket["pass"]+=1
        value=num(row.get("success"))
        if value is not None:
            bucket["success"].append(value)
    return buckets

def feature_history(weekly, season, week):
    values={}
    for (s,w),teams in weekly.items():
        if s!=season or w>=week:
            continue
        for team,row in teams.items():
            values.setdefault(team,[]).append((w,row))
    result={}
    for team,rows in values.items():
        rows=sorted(rows)[-5:]
        plays=sum(x["plays"] for _,x in rows)
        successes=[v for _,x in rows for v in x["success"]]
        if plays and successes:
            result[team]={"plays_per_game":plays/len(rows),"success_rate":sum(successes)/len(successes),
                          "neutral_pass_proxy":sum(x["pass"] for _,x in rows)/plays}
    return result

def candidate(v2, home, away, means):
    total_adjust=max(-MAX_TOTAL_ADJUSTMENT,min(MAX_TOTAL_ADJUSTMENT,
       PACE_POINTS_PER_PLAY*((home["plays_per_game"]+away["plays_per_game"])-2*means["plays_per_game"])))
    margin_adjust=max(-MAX_MARGIN_ADJUSTMENT,min(MAX_MARGIN_ADJUSTMENT,
       SUCCESS_MARGIN_POINTS*(home["success_rate"]-away["success_rate"])
       +PASS_MARGIN_POINTS*(home["neutral_pass_proxy"]-away["neutral_pass_proxy"])))
    total=max(1.0,v2["pred_total"]+total_adjust)
    margin=v2["pred_margin"]+margin_adjust
    return total,margin

def evaluate(schedules, pbp):
    schedules=[g for g in schedules if g.get("game_type","REG")=="REG" and num(g.get("home_score")) is not None and num(g.get("away_score")) is not None]
    team_games=[]
    for row in pbp:
        try:
            if row.get("play_type") not in ("pass","run"): continue
            for team,off,defn in ((row.get("posteam"),row.get("epa"),None),(row.get("defteam"),None,row.get("epa"))):
                # Team EPA is aggregated below; this branch only validates schema.
                pass
        except AttributeError: continue
    by_team=defaultdict(lambda: {"off":[],"def":[]})
    for row in pbp:
        try:
            if row.get("play_type") not in ("pass","run"): continue
            season,week,gid=int(row["season"]),int(row["week"]),str(row["game_id"])
            epa=num(row.get("epa"))
            if epa is None: continue
            if row.get("posteam"): by_team[(season,week,gid,row["posteam"])]["off"].append(epa)
            if row.get("defteam"): by_team[(season,week,gid,row["defteam"])]["def"].append(epa)
        except (KeyError,TypeError,ValueError): continue
    for (season,week,gid,team),values in by_team.items():
        if values["off"] and values["def"]:
            team_games.append({"season":season,"week":week,"game_id":gid,"team":team,
                               "offense_epa":sum(values["off"])/len(values["off"]),
                               "defense_epa":sum(values["def"])/len(values["def"])})
    baseline=build_v2_predictions(schedules,team_games)
    by_game={str(x["game_id"]):x for x in baseline}
    weekly=weekly_features(pbp,schedules)
    rows=[]
    for season,week in sorted({(int(g["season"]),int(g["week"])) for g in schedules}):
        features=feature_history(weekly,season,week)
        if len(features)<2: continue
        means={key:sum(x[key] for x in features.values())/len(features) for key in ("plays_per_game","success_rate","neutral_pass_proxy")}
        for game in (g for g in schedules if int(g["season"])==season and int(g["week"])==week):
            base=by_game.get(str(game["game_id"]))
            home,away=game.get("home_team"),game.get("away_team")
            if not base or home not in features or away not in features: continue
            v3_total,v3_margin=candidate(base,features[home],features[away],means)
            actual_margin=num(game["home_score"])-num(game["away_score"])
            actual_total=num(game["home_score"])+num(game["away_score"])
            rows.append({"season":season,"week":week,"game_id":str(game["game_id"]),
              "v2_margin":base["pred_margin"],"v2_total":base["pred_total"],
              "v3_margin":v3_margin,"v3_total":v3_total,"actual_margin":actual_margin,"actual_total":actual_total})
    return rows

def summarize(rows):
    def block(records):
        out={}
        for market,actual in (("margin","actual_margin"),("total","actual_total")):
            for model in ("v2","v3"):
                out[f"{model}_{market}"]=metric([r[f"{model}_{market}"]-r[actual] for r in records])
        for model in ("v2","v3"):
            out[f"{model}_winner_accuracy"]=round(sum((r[f"{model}_margin"]>0)==(r["actual_margin"]>0) for r in records)/len(records),4) if records else None
        return out
    dev=[r for r in rows if r["season"]==2024]
    holdout=[r for r in rows if r["season"]==2025]
    return {"development_2024":block(dev),"holdout_2025":block(holdout),
      "holdout_games":len(holdout),
      "eligible_for_review":len(holdout)>=200,
      "promotion_approved":False,
      "limitations":["No sportsbook lines: ATS and O/U hit rates are intentionally omitted.","V3 coefficients are predeclared hypotheses, not fitted on this holdout.","This is a historical replay; live V2 remains unchanged."]}

def main():
    import argparse
    import nflreadpy as nfl
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    seasons=[2024,2025]
    rows=evaluate(nfl.load_schedules(seasons).to_dicts(),nfl.load_pbp(seasons).to_dicts())
    result={"status":"research_only_historical_replay","models":["FOURTHDOWN v2 replay","FOURTHDOWN v3 feature shadow"],
            "results":summarize(rows)}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    if not result["results"]["eligible_for_review"]:
        raise RuntimeError("Fewer than 200 2025 holdout games were available")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
