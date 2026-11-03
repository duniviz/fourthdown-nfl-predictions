#!/usr/bin/env python3
"""Multi-season paired passing-yards championship; never promotes a production model."""
import argparse,csv,json,math
from pathlib import Path
from passing_yards_model_lab import evaluate,VARIANTS

def compare(season_rows,holdout_weeks=4):
 seasons={}
 for season,rows in sorted(season_rows.items()):
  completed=sorted({int(r["week"]) for r in rows if r.get("season")==str(season) and r.get("week","").isdigit() and r.get("season_type","REG")=="REG" and r.get("passing_yards") not in ("",None)})
  if not completed or max(completed)<8:
   seasons[str(season)]={"status":"insufficient_history","through_week":max(completed) if completed else None}
   continue
  result=evaluate(rows,season,max(completed),holdout_weeks=holdout_weeks)
  seasons[str(season)]={"status":"evaluated","through_week":max(completed),"holdout_weeks":result["holdout_weeks"],
    "development":result["results"]["development"],"holdout":result["results"]["holdout"],
    "samples":result["samples"]}
 evaluated=[v for v in seasons.values() if v["status"]=="evaluated"]
 totals={}
 for variant in VARIANTS:
  entries=[s["holdout"][variant] for s in evaluated if s["holdout"][variant]["samples"]]
  n=sum(x["samples"] for x in entries)
  totals[variant]={"samples":n,"mae":round(sum(x["mae"]*x["samples"] for x in entries)/n,2),
   "rmse":round(math.sqrt(sum(x["rmse"]**2*x["samples"] for x in entries)/n),2)} if n else {"samples":0,"mae":None,"rmse":None}
 baseline=totals["baseline"]
 comparison={}
 for variant in VARIANTS:
  if variant=="baseline":continue
  wins=[]
  for year,s in seasons.items():
   if s["status"]!="evaluated":continue
   a=s["holdout"][variant];ref=s["holdout"]["baseline"]
   wins.append({"season":int(year),"samples":a["samples"],"improved_mae":a["mae"]<ref["mae"] if a["samples"] else False,
    "improved_rmse":a["rmse"]<ref["rmse"] if a["samples"] else False})
  current=totals[variant]
  comparison[variant]={"holdout_by_season":wins,"all_seasons_improved":len(wins)>=3 and all(x["samples"]>=20 and x["improved_mae"] and x["improved_rmse"] for x in wins),
   "pooled_mae_improved":current["mae"] is not None and baseline["mae"] is not None and current["mae"]<baseline["mae"],
   "pooled_rmse_improved":current["rmse"] is not None and baseline["rmse"] is not None and current["rmse"]<baseline["rmse"]}
 candidates=[name for name,x in comparison.items() if x["all_seasons_improved"] and x["pooled_mae_improved"] and x["pooled_rmse_improved"]]
 return {"status":"multi_season_research_only","seasons":seasons,"pooled_holdout":totals,"comparison":comparison,
  "consistent_candidates":candidates,"production_change_approved":False,
  "note":"Each season is tested using only prior weeks from that same season. Holdout is the last completed weeks of each season. The 2026 holdout is preliminary and must not be treated as a fully independent future season. Pooled metrics are sample-weighted approximations from rounded per-season metrics. No model changes or bet recommendations."}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--season-csv",type=Path,action="append",required=True,help="Repeat for each season's weekly CSV")
 p.add_argument("--holdout-weeks",type=int,default=4)
 p.add_argument("--output",type=Path,required=True)
 a=p.parse_args()
 if a.holdout_weeks<2:p.error("Require at least two holdout weeks")
 datasets={}
 for path in a.season_csv:
  with path.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
  found={int(x["season"]) for x in rows if x.get("season","").isdigit()}
  if len(found)!=1:raise ValueError("Expected one season per CSV: "+str(path))
  season=found.pop()
  if season in datasets:raise ValueError("Duplicate season: "+str(season))
  datasets[season]=rows
 result=compare(datasets,a.holdout_weeks)
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(result,indent=2)+"\n")
 print("Multi-season championship:",{"seasons":list(result["seasons"]),"holdout":result["pooled_holdout"],"consistent_candidates":result["consistent_candidates"],"production_changed":False})
if __name__=="__main__":main()
