#!/usr/bin/env python3
"""Aggregate matched-sample historical challenger tests without auto-promoting."""
import argparse,json
from pathlib import Path
MARKETS=("passing_yards","rushing_yards","receiving_yards")
def compare(reports):
 result={"status":"research_only_pending_production_comparison","production_changed":False,"display_model_changed":False,"markets":{},"limitations":["Research baseline is the weekly historical model, NOT the live photo-card production model.","Live Prop Desk and V3 forecasts must be archived and graded on identical games before declaring a display winner.","Cross-season qualifying challengers are candidates, not automatically approved replacements."]}
 for market in MARKETS:
  seasons={};common=None
  for report in reports:
   if report.get("status")!="research_only":continue
   season=report["season"];dev=report["results"]["development"][market];hold=report["results"]["holdout"][market]
   valid=[]
   for variant,score in hold.items():
    d=dev[variant]
    if score["samples"]>=20 and d["samples"]>=30 and score["mae"] is not None and d["mae"] is not None:
     valid.append(variant)
   seasons[str(season)]={"holdout":{v:hold[v] for v in valid},"development":{v:dev[v] for v in valid}}
   winning={v for v in valid if v!="baseline" and all(part[v][k]<part["baseline"][k] for part in (dev,hold) for k in ("mae","rmse"))}
   common=winning if common is None else common&winning
  result["markets"][market]={"season_results":seasons,"repeatable_research_candidates":sorted(common or []),"display_decision":"retain_current_pending_matched_live_model_backtest"}
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument("--report",action="append",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 out=compare([json.loads(f.read_text()) for f in a.report]);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+"\n")
 print("Head-to-head research report:",{k:v["repeatable_research_candidates"] for k,v in out["markets"].items()},"no production or display promotion")
if __name__=="__main__":main()
