#!/usr/bin/env python3
"""Research-only player yards projection from historical nflverse weekly data."""
import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

FIELDS={"passing_yards":"passing_yards","rushing_yards":"rushing_yards","receiving_yards":"receiving_yards"}

def project(rows, season, week, min_games=3):
    history=defaultdict(lambda:defaultdict(list))
    for r in rows:
        try:
            if int(r["season"]) != season or int(r["week"]) >= week or int(r["week"]) < 1:
                continue
            if r.get("season_type","REG") != "REG":
                continue
        except (KeyError, ValueError, TypeError):
            continue
        pid=r.get("player_id") or r.get("gsis_id")
        if not pid:
            continue
        for market, field in FIELDS.items():
            try:
                v=float(r[field])
            except (KeyError, ValueError, TypeError):
                continue
            if not (0 <= v <= 700):
                continue
            history[(pid,r.get("player_name") or r.get("player_display_name") or pid,r.get("recent_team") or r.get("team") or "")][market].append((int(r["week"]),v))
    result=[]
    for (pid,name,team), markets in history.items():
        for market, vals in markets.items():
            vals.sort()
            if len(vals)<min_games:
                continue
            recent=vals[-5:]
            # Shrunk recent mean vs full season mean, no post-cutoff information.
            mean=sum(v for _,v in vals)/len(vals)
            recent_mean=sum(v for _,v in recent)/len(recent)
            estimate=round(.65*recent_mean+.35*mean,1)
            result.append({"player_id":pid,"player_name":name,"team":team,
                           "market":market,"projected_yards":estimate,
                           "games_used":len(vals),"latest_week_used":vals[-1][0]})
    return sorted(result,key=lambda x:(x["market"],x["player_name"],x["player_id"]))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--weekly-csv",type=Path,required=True)
    p.add_argument("--season",type=int,required=True)
    p.add_argument("--week",type=int,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if not 2<=a.week<=18:
        p.error("Week must be 2..18")
    if a.output.resolve().is_relative_to((Path(__file__).resolve().parents[1]/"data").resolve()):
        p.error("Research cannot overwrite published data")
    with a.weekly_csv.open(newline="",encoding="utf-8-sig") as f:
        result=project(csv.DictReader(f),a.season,a.week)
    if not result:
        p.error("No eligible historical player samples")
    payload={"season":a.season,"week":a.week,"generated_at_utc":datetime.now(timezone.utc).isoformat(),
             "status":"research_only_uncalibrated","source":"supplied_nflverse_weekly_csv",
             "note":"Not opponent, injury, snap, or playing-status adjusted; inactive players may appear",
             "projections":result}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(payload,indent=2)+"\n")
    print(f"Wrote {len(result)} research player-market estimates, NOT published")
if __name__=="__main__":
    main()
