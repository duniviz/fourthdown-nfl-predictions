#!/usr/bin/env python3
"""Leak-free V2 ATS/O/U backtest using an aligned historical line file."""
import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from backtest.v2 import build_v2_predictions

EDGE_THRESHOLDS = (0.0, 1.0, 1.5, 2.0, 3.0, 4.0)

def number(value):
    try:
        value=float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None

def team_epa_rows(pbp):
    buckets=defaultdict(lambda: {"off":[],"def":[]})
    for row in pbp:
        try:
            if row.get("play_type") not in ("pass","run"): continue
            season,week,gid=int(row["season"]),int(row["week"]),str(row["game_id"])
            epa=number(row.get("epa"))
            if epa is None: continue
        except (KeyError,TypeError,ValueError): continue
        if row.get("posteam"): buckets[(season,week,gid,row["posteam"])]["off"].append(epa)
        if row.get("defteam"): buckets[(season,week,gid,row["defteam"])]["def"].append(epa)
    return [{"season":season,"week":week,"game_id":gid,"team":team,
             "offense_epa":sum(v["off"])/len(v["off"]),"defense_epa":sum(v["def"])/len(v["def"])}
            for (season,week,gid,team),v in buckets.items() if v["off"] and v["def"]]

def read_lines(path):
    with path.open(newline="",encoding="utf-8-sig") as f:
        raw=list(csv.DictReader(f))
    rows=[]
    for r in raw:
        try:
            row={k.lower().strip():str(v).strip() for k,v in r.items()}
            values={"week":int(row["week"]),"away":row["away_team"].upper(),"home":row["home_team"].upper(),
                    "away_score":number(row["away_score"]),"home_score":number(row["home_score"]),
                    "home_spread":number(row["closing_home_spread"]),"total_line":number(row["closing_total"])}
            if not values["away"] or not values["home"] or any(values[x] is None for x in ("away_score","home_score","home_spread","total_line")): continue
            rows.append(values)
        except (KeyError,ValueError): continue
    return rows

def summarize(rows):
    wins=sum(x["grade"]=="win" for x in rows);losses=sum(x["grade"]=="loss" for x in rows);pushes=sum(x["grade"]=="push" for x in rows)
    return {"picks":len(rows),"wins":wins,"losses":losses,"pushes":pushes,
            "win_rate_pct":round(100*wins/(wins+losses),1) if wins+losses else None,
            "mean_model_edge_points":round(sum(abs(x["edge"]) for x in rows)/len(rows),2) if rows else None}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--csv",type=Path,required=True)
    ap.add_argument("--season",type=int,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    import nflreadpy as nfl
    schedules=nfl.load_schedules([args.season-1,args.season]).to_dicts()
    predictions=[x for x in build_v2_predictions(schedules,team_epa_rows(nfl.load_pbp([args.season-1,args.season]).to_dicts())) if x["season"]==args.season]
    lines=read_lines(args.csv)
    by_matchup={(x["week"],x["away"],x["home"]):x for x in lines}
    matched=[];score_mismatches=[]
    for forecast in predictions:
        line=by_matchup.get((forecast["week"],forecast["away_team"],forecast["home_team"]))
        if not line: continue
        actual_away=round((forecast["actual_total"]-forecast["actual_margin"])/2,3)
        actual_home=round((forecast["actual_total"]+forecast["actual_margin"])/2,3)
        if line["away_score"]!=actual_away or line["home_score"]!=actual_home:
            score_mismatches.append({"week":forecast["week"],"away":forecast["away_team"],"home":forecast["home_team"],
                                     "csv_score":[line["away_score"],line["home_score"]],"official_score":[actual_away,actual_home]})
            continue
        margin,total=forecast["actual_margin"],forecast["actual_total"]
        matched.append({"forecast":forecast,"line":line,
                        "ats_result":"home" if margin+line["home_spread"]>0 else "away" if margin+line["home_spread"]<0 else "push",
                        "ou_result":"over" if total>line["total_line"] else "under" if total<line["total_line"] else "push"})
    threshold_results={}
    for threshold in EDGE_THRESHOLDS:
        ats=[];ou=[]
        for row in matched:
            forecast,line=row["forecast"],row["line"]
            edge=forecast["pred_margin"]+line["home_spread"]
            if abs(edge)>threshold:
                pick="home" if edge>0 else "away"
                ats.append({"edge":edge,"grade":"push" if row["ats_result"]=="push" else "win" if pick==row["ats_result"] else "loss"})
            edge=forecast["pred_total"]-line["total_line"]
            if abs(edge)>threshold:
                pick="over" if edge>0 else "under"
                ou.append({"edge":edge,"grade":"push" if row["ou_result"]=="push" else "win" if pick==row["ou_result"] else "loss"})
        threshold_results[str(threshold)]={"ats":summarize(ats),"over_under":summarize(ou)}
    valid=len(matched)>=190 and not score_mismatches
    result={"status":"research_only_historical_replay" if valid else "invalid_schedule_or_score_alignment",
            "season":args.season,"source_csv_rows":len(lines),"eligible_pregame_v2_forecasts":len(predictions),
            "matched_score_verified_forecasts":len(matched),"score_mismatches":score_mismatches[:20],
            "edge_thresholds":threshold_results,
            "conventions":{"closing_home_spread":"Input is treated as the home team's closing spread.","ats_edge":"projected home margin plus home closing spread.","total_edge":"projected total minus closing total."},
            "limitations":["Closing lines without prices/juice support hit-rate analysis only, not ROI.","Thresholds are predeclared and reported side by side.","The model does not use market lines as inputs."]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    if not valid:
        raise RuntimeError("Line file did not pass schedule/score alignment; refusing to report ATS/O/U performance.")

if __name__=="__main__": main()
