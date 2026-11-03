#!/usr/bin/env python3
"""Weekly model governance: rank challengers and refuse unsafe promotions."""
import json
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def decisions(player,weather):
    output={}
    for market,entry in player.get("markets",{}).items():
        if entry.get("status")!="evaluated":continue
        base=entry["baseline_mae"]
        ranked=sorted(entry["challengers"].items(),key=lambda item:item[1]["mae"])
        if not ranked:continue
        name,score=ranked[0]
        gain=(base-score["mae"])/base if base>0 else 0
        sample=entry.get("holdout",0)
        eligible=sample>=300 and gain>=.02
        output[market]={"champion":"existing_live_model","best_challenger":name,
                        "holdout_samples":sample,"improvement_pct":round(100*gain,2),
                        "research_candidate":eligible,
                        "decision":"candidate_needs_live_equivalence_and_independent_forward_test" if eligible else "retain_champion",
                        "production_changed":False}
    return {"generated_at_utc":datetime.now(timezone.utc).isoformat(),
            "decisions":output,"weather_status":weather.get("status","unavailable"),
            "automatic_promotion_enabled":False,"live_weights_changed":False,
            "blockers":["No verified equivalence between historical challenger features and production inputs",
                        "No independent forward shadow comparison against frozen live projections",
                        "No deployed model artifact and atomic rollback mechanism"],
            "policy":{"min_holdout_samples":300,"min_relative_mae_improvement":.02,
                      "require_forward_shadow_validation":True,"require_atomic_rollback":True},
            "note":"Automated research selection only. Never modify production based on retrospective scores alone."}
def main():
    player=json.loads((ROOT/"data/ml-challenger-review.json").read_text())
    weather=json.loads((ROOT/"data/weather-wednesday-review.json").read_text())
    report=decisions(player,weather)
    (ROOT/"data/model-governance.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
