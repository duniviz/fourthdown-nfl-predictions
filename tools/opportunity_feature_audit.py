"""Fail-closed audit for opportunity-first player modeling.

Only verifies whether the historical backtest contains pregame workload features.
Never estimates targets, routes, carries, or snap shares from postgame outcomes.
"""
import csv
import json
from pathlib import Path

REQUIRED={"season","week","player_id","market","actual","new"}
OPPORTUNITY={
    "receiving_yards":("expected_targets","projected_targets","expected_routes","projected_routes","expected_catch_rate","expected_yards_per_catch"),
    "rushing_yards":("expected_carries","projected_carries","expected_yards_per_carry","projected_snap_share"),
    "passing_yards":("expected_pass_attempts","projected_pass_attempts","expected_yards_per_attempt"),
}
def audit(path):
    with Path(path).open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        fields=set(reader.fieldnames or ())
        if not REQUIRED.issubset(fields):
            raise ValueError("Historical backtest is missing mandatory columns")
        rows=list(reader)
    if not rows:
        raise ValueError("Empty historical backtest")
    report={}
    for market,features in OPPORTUNITY.items():
        subset=[r for r in rows if r.get("market")==market]
        present=[f for f in features if f in fields]
        nonempty={f:sum(bool(r.get(f,"").strip()) for r in subset) for f in present}
        report[market]={"historical_rows":len(subset),"candidate_features":list(features),
                        "present_columns":present,"nonempty_feature_rows":nonempty,
                        "eligible_for_opportunity_training":bool(subset) and all(nonempty.get(f,0)==len(subset) for f in features)}
    return {"status":"feature_availability_audit","research_only":True,"production_changed":False,
            "trained_model":False,"postgame_workload_used_as_pregame":False,
            "source":"data/backtests/player-predictions.csv","markets":report,
            "next_step":"Collect timestamped pregame opportunity features and freeze them before kickoff; validate same-slate joins before training."}
def main():
    result=audit("data/backtests/player-predictions.csv")
    Path("data/opportunity-feature-audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print("Opportunity feature audit:",{k:v["eligible_for_opportunity_training"] for k,v in result["markets"].items()})
if __name__=="__main__":main()
