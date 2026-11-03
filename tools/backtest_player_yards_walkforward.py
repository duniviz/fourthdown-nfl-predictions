#!/usr/bin/env python3
"""Strictly walk-forward historical player-yards accuracy audit, no betting probabilities."""
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path
from project_player_yards import project,FIELDS

def evaluate(rows,season,last_week,min_games=3):
    actual=defaultdict(list)
    for row in rows:
        try:
            if int(row["season"])!=season or row.get("season_type","REG")!="REG":continue
            week=int(row["week"])
            if not 1<=week<=last_week:continue
            pid=row.get("player_id") or row.get("gsis_id")
            if not pid:continue
            for market in FIELDS:
                value=float(row[market])
                if math.isfinite(value) and 0<=value<=700:
                    actual[(week,pid,market)].append(value)
        except (ValueError,TypeError,KeyError):continue
    errors=defaultdict(list)
    weeks={}
    for week in range(min_games+1,last_week+1):
        forecasts=project(rows,season,week,min_games=min_games)
        evaluated=0
        for p in forecasts:
            observed=actual.get((week,p["player_id"],p["market"]))
            if not observed or len(observed)!=1:continue
            if int(p["latest_week_used"])>=week:raise ValueError("Future leakage detected")
            error=float(p["projected_yards"])-observed[0]
            errors[p["market"]].append(error)
            evaluated+=1
        weeks[str(week)]={"evaluated":evaluated}
    markets={}
    for market,values in errors.items():
        n=len(values)
        markets[market]={"samples":n,"mae":round(sum(abs(e) for e in values)/n,2),"rmse":round(math.sqrt(sum(e*e for e in values)/n),2),"bias":round(sum(values)/n,2)}
    return {"status":"historical_walk_forward_research_only","season":season,"through_week":last_week,"markets":markets,"weeks":weeks,"note":"Predictions use only prior weeks; metrics are conditional on historical observed players and do not measure DK betting returns or calibrated probabilities."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--weekly-csv",type=Path,required=True)
    p.add_argument("--season",type=int,required=True)
    p.add_argument("--through-week",type=int,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    with a.weekly_csv.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
    result=evaluate(rows,a.season,a.through_week)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print("Walk-forward accuracy:",result["markets"])
if __name__=="__main__":main()
