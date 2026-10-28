#!/usr/bin/env python3
"""Walk-forward player yardage baseline test; no future-week leakage."""
import argparse
import csv
import json
from collections import defaultdict
from math import fsum
from pathlib import Path
from project_player_yards import FIELDS, project

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
    for week in range(a.first_week,a.last_week+1):
        preds=project(rows,a.season,week)
        keyed={(x["player_id"],x["market"]):x["projected_yards"] for x in preds}
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
                    errors[market].append(abs(actual-keyed[(pid,market)]))
    print(json.dumps({"season":a.season,"weeks":[a.first_week,a.last_week],
        "markets":{k:{"observations":len(v),"mae":round(fsum(v)/len(v),2)} for k,v in errors.items() if v},
        "warning":"Research-only in-sample player selection; compare with a prior-only baseline before deployment"},indent=2))
if __name__=="__main__":
    main()
