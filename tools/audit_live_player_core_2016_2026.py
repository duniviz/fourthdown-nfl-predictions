#!/usr/bin/env python3
"""Independent chronological audit of production's shared yardage core versus research challenger.

This does NOT replay the entire live publishing pipeline (injuries, QB role,
availability, weather, game script); it must not authorize deployment.
"""
import argparse,json
from collections import defaultdict
from pathlib import Path
import nflreadpy as nfl
from live.player_research import project_yards, METRICS, num
from live.backtest_players import backtest

YARDS={"passing_yards","rushing_yards","receiving_yards"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",type=int,default=2016)
    p.add_argument("--end",type=int,default=2026)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    seasons=tuple(range(a.start,a.end+1))
    # Existing paired challenger uses exactly the same prior-week history cohort.
    challenger=backtest(seasons)
    # For direct shared-core comparison, reconstruct prior player records.
    grouped=defaultdict(list)
    for season in seasons:
        raw=nfl.load_player_stats([season],summary_level="week").to_dicts()
        for row in raw:
            if str(row.get("season_type","REG")).upper() not in ("REG","2"):continue
            try:week=int(row["week"])
            except (ValueError,TypeError,KeyError):continue
            if not 1<=week<=18 or not row.get("player_id") or not row.get("team"):continue
            grouped[(season,str(row["team"]),str(row["player_id"]))].append(row)
    for records in grouped.values():records.sort(key=lambda r:int(r["week"]))
    volume_for={metric:volume for metric,_,volume in METRICS}
    results=defaultdict(list)
    for r in challenger:
        metric=r["market"]
        if metric not in YARDS:continue
        records=grouped[(r["season"],r["team"],r["player_id"])]
        past=[x for x in records if int(x["week"])<r["week"]]
        if len(past)<3:continue
        current,_,_,_=project_yards(past,metric,volume_for[metric])
        results[(r["season"],metric)].append((abs(current-r["actual"]),abs(r["new"]-r["actual"])))
    report={"status":"research_only","production_changed":False,"full_live_replay":False,
            "note":"Production shared core vs historical challenger on paired observed-player weeks. Full live role, availability, game-script and published frozen predictions are NOT replayed; never auto-promote from this report.",
            "by_season":{},"overall":{}}
    for market in sorted(YARDS):
        combined=[]
        for season in seasons:
            pair=results[(season,market)]
            if not pair:continue
            combined+=pair
            report["by_season"].setdefault(str(season),{})[market]={"samples":len(pair),"production_core_mae":round(sum(x for x,_ in pair)/len(pair),3),"challenger_mae":round(sum(y for _,y in pair)/len(pair),3)}
        if combined:
            n=len(combined);old=sum(x for x,_ in combined)/n;new=sum(y for _,y in combined)/n
            report["overall"][market]={"samples":n,"production_core_mae":round(old,3),"challenger_mae":round(new,3),"improvement_pct":round((old-new)/old*100,2) if old else None,"approved_for_promotion":False}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report["overall"],indent=2))
if __name__=="__main__":main()
