#!/usr/bin/env python3
"""Inspect player stats coverage before trying to forecast target season."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument("--csv",type=Path,required=True)
p.add_argument("--season",type=int,required=True)
p.add_argument("--week",type=int,required=True)
a=p.parse_args()
with a.csv.open(newline="",encoding="utf-8-sig") as f:
    reader=csv.DictReader(f)
    cols=reader.fieldnames or []
    counts=Counter()
    before=0
    examples=[]
    for row in reader:
        season=row.get("season","")
        counts[season]+=1
        if season==str(a.season):
            try:
                if int(row.get("week","0"))<a.week:
                    before+=1
                    if len(examples)<3:
                        examples.append({k:row.get(k) for k in ("player_id","player_name","season_type","week","passing_yards","rushing_yards","receiving_yards")})
            except ValueError:
                pass
report={"columns":cols,"rows_by_season":dict(counts),"target_season":a.season,
        "rows_before_target_week":before,"sample_target_rows":examples,
        "has_target_history":before>0}
print(json.dumps(report,indent=2))
if before==0:
    raise SystemExit(f"Player feed contains no {a.season} data before week {a.week}; check source freshness, do not use old season as current")
