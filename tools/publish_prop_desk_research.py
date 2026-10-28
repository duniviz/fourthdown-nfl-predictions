#!/usr/bin/env python3
"""Publish research-only Prop Desk snapshot; never manufacture betting confidence."""
import argparse,json
from pathlib import Path

def build(rank, calibration):
    markets={}
    for name,m in calibration.get("markets",{}).items():
        markets[name]={"status":m.get("status","unavailable"),"train_samples":m.get("train_samples",0),
                       "holdout_samples":m.get("holdout_samples",0),"holdout_interval_coverage":m.get("holdout_interval_coverage"),
                       "holdout_brier":m.get("holdout_brier")}
    rows=[]
    for r in rank.get("comparisons",[]):
        if r.get("availability_status") in {"out","inactive","doubtful","ir","suspended"}:
            continue
        rows.append({k:r.get(k) for k in ("player_id","player_name","team","opponent","market","projected_yards",
          "dk_line","difference_yards","over_price","under_price","last_update","match_status",
          "availability_status","provisional_research_status","ranking_status","block_reasons",
          "research_over_probability","research_interval_80_yards")})
    return {"status":"research_only_not_betting_recommendations","season":rank.get("season"),"week":rank.get("week"),
            "generated_at_utc":rank.get("generated_at_utc"),"counts":rank.get("counts",{}),
            "market_validation":markets,"comparisons":rows,
            "note":"Provisional means presumed available, not confirmed active. Historical residual validation is not DK-line-specific. No automated picks or calibrated betting edges."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ranking-json",type=Path,required=True)
    p.add_argument("--calibration-json",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    rank=json.loads(a.ranking_json.read_text())
    cal=json.loads(a.calibration_json.read_text())
    if not rank.get("comparisons") or rank.get("status")!="research_only_no_bet_ranking":
        raise SystemExit("Missing or invalid research diagnostics; refusing publication")
    output=build(rank,cal)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(output,indent=2)+"\n")
    print("Prop Desk research published:",output["counts"])
if __name__=="__main__":main()
