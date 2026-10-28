#!/usr/bin/env python3
"""Walk-forward player yardage baseline test; no future-week leakage."""
import argparse
import csv
import json
from collections import defaultdict
from math import fsum
from pathlib import Path
from project_player_yards import FIELDS, project, opponent_defense

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--weekly-csv",type=Path,required=True)
    p.add_argument("--season",type=int,required=True)
    p.add_argument("--first-week",type=int,default=5)
    p.add_argument("--last-week",type=int,default=18)
    a=p.parse_args()
    if not 2<=a.first_week<=a.last_week<=18:
        p.error("Invalid week range")
    with a.weekly_csv.open(newline="",encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    errors=defaultdict(list)
    naive_errors=defaultdict(list)
    adjusted_errors=defaultdict(list)
    adjusted_coverage=defaultdict(int)
    matched=defaultdict(int)
    for week in range(a.first_week,a.last_week+1):
        preds=project(rows,a.season,week)
        keyed={(x["player_id"],x["market"]):x["projected_yards"] for x in preds}
        factors=opponent_defense(rows,a.season,week)
        prior=defaultdict(list)
        for row in rows:
            try:
                if int(row["season"])!=a.season or int(row["week"])>=week or row.get("season_type","REG")!="REG":
                    continue
            except (ValueError,KeyError,TypeError):
                continue
            pid0=row.get("player_id") or row.get("gsis_id")
            for m,f in FIELDS.items():
                try:
                    prior[(pid0,m)].append((int(row["week"]),float(row[f])))
                except (ValueError,KeyError,TypeError):
                    pass
        for r in rows:
            try:
                if int(r["season"])!=a.season or int(r["week"])!=week or r.get("season_type","REG")!="REG":
                    continue
            except (KeyError,ValueError,TypeError):
                continue
            pid=r.get("player_id") or r.get("gsis_id")
            for market,field in FIELDS.items():
                if (pid,market) not in keyed:
                    continue
                try:
                    actual=float(r[field])
                except (ValueError,TypeError,KeyError):
                    continue
                if 0<=actual<=700:
                    base=keyed[(pid,market)]
                    errors[market].append(abs(actual-base))
                    opponent=(r.get("opponent_team") or "").strip()
                    factor=factors.get((opponent,market),1.0)
                    adjusted_errors[market].append(abs(actual-round(base*factor,1)))
                    if (opponent,market) in factors:
                        adjusted_coverage[market]+=1
                    hist=sorted(prior.get((pid,market),[]))
                    if hist:
                        naive=sum(v for _,v in hist[-3:])/len(hist[-3:])
                        naive_errors[market].append(abs(actual-naive))
                    matched[market]+=1
    print(json.dumps({"season":a.season,"weeks":[a.first_week,a.last_week],
        "markets":{k:{"observations":len(v),"mae":round(fsum(v)/len(v),2),
            "opponent_adjusted_mae":round(fsum(adjusted_errors[k])/len(adjusted_errors[k]),2),
            "opponent_adjusted_observations":adjusted_coverage[k],
            "adjustment_improved_mae":fsum(adjusted_errors[k])<fsum(v),
            "last_3_games_mae":round(fsum(naive_errors[k])/len(naive_errors[k]),2) if naive_errors[k] else None} for k,v in errors.items() if v},
        "warning":"Walk-forward, prior-only role selection and defense; observed-player evaluation only, not an availability or betting-profit test. If opponent_adjusted_observations is zero, adjusted equals base and is not a validated improvement."},indent=2))
if __name__=="__main__":
    main()
