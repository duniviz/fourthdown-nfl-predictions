#!/usr/bin/env python3
"""Persisted research-only challenger registry. Never changes production models."""
import argparse,json
from pathlib import Path
CANDIDATES={
 "passing_yards":["proe","opponent_adjusted_epa","neutral_pace","pressure_sack","rolling_3","rolling_5","ewma","bayesian_shrinkage"],
 "rushing_yards":["proe","neutral_pace","expected_yards","rolling_3","rolling_5","ewma","bayesian_shrinkage"],
 "receiving_yards":["wopr","expected_yards","air_yards","opportunity_rate","rolling_3","rolling_5","ewma","bayesian_shrinkage"],
 "touchdowns":["expected_touchdowns","red_zone_share","opponent_adjusted_epa","bayesian_shrinkage"],
 "scores":["opponent_adjusted_epa","neutral_pace","explosive_play_rate","red_zone_share","rolling_3","rolling_5","ewma"],
 "spreads":["opponent_adjusted_epa","neutral_pace","pressure_sack","bayesian_shrinkage"],
 "totals":["opponent_adjusted_epa","neutral_pace","explosive_play_rate","red_zone_share"]
}
def registry(reports):
 result={"status":"research_only","production_changed":False,"automatic_promotion":False,"markets":{}}
 for market,features in CANDIDATES.items():
  result["markets"][market]={"champion":"current_production","challengers":{f:{"status":"awaiting_validated_data_and_backtest","eligible_for_promotion":False} for f in features}}
 for path in reports:
  data=json.loads(Path(path).read_text())
  result.setdefault("completed_reports",[]).append({"file":Path(path).name,"season":data.get("season"),"status":data.get("status"),"candidates":data.get("candidate_improvements",[])})
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument("--reports",nargs="*",default=[]);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 result=registry(a.reports);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n")
 print("Challenger registry:",len(result["markets"]),"markets; production unchanged")
if __name__=="__main__":main()
