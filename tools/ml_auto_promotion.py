"""Automatic weekly champion/challenger decision policy.

Only deployable challengers can be promoted. A research-only backtest is
insufficient evidence of production equivalence.
"""
import json
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def decide(report,registry):
    markets={}
    for market,info in report.get("markets",{}).items():
        incumbent=registry.get("markets",{}).get(market,{"champion":"baseline","version":"original"})
        result={"champion":incumbent["champion"],"version":incumbent.get("version","original"),
                "action":"keep","reason":"insufficient validated evidence"}
        # A research leaderboard is not a deployable production validation.
        # Require an explicit independent replay, multiweek stability,
        # cross-market regression check and tested rollback before any promotion.
        safety=info.get("production_validation") or {}
        verified=all(safety.get(flag) is True for flag in (
            "independent_chronological_replay_passed",
            "multiweek_stability_passed",
            "cross_market_regression_passed",
            "rollback_test_passed"))
        if not verified:
            result["reason"]="production replay, multiweek stability, regression or rollback evidence missing"
        elif info.get("status")!="evaluated" or info.get("holdout",0)<300:
            result["reason"]="insufficient holdout"
        else:
            baseline=info.get("baseline_mae",0)
            candidates=[(name,data) for name,data in info.get("challengers",{}).items()
                        if baseline>0 and data.get("mae",float("inf"))<=baseline*.97]
            candidates.sort(key=lambda pair:pair[1]["mae"])
            if not candidates:
                result["reason"]="no challenger exceeds 3% MAE improvement threshold"
            elif not registry.get("deployable",{}).get(market,{}).get(candidates[0][0],False):
                result["reason"]="best challenger is not yet production-equivalent and deployable"
                result["research_candidate"]=candidates[0][0]
            else:
                # A production integration must explicitly publish a compatible artifact,
                # with rollback and frozen holdout verification before switching.
                artifact=registry.get("artifacts",{}).get(market,{}).get(candidates[0][0])
                if not artifact:
                    result["reason"]="missing validated production artifact"
                else:
                    result.update({"action":"promote","champion":candidates[0][0],
                                   "version":artifact,"reason":"passed promotion gates"})
        markets[market]=result
    return {"generated_at_utc":datetime.now(timezone.utc).isoformat(),
            "policy":"minimum 300 holdout samples, >=3% MAE improvement, deployable artifact required",
            "markets":markets,"automatic_promotion_enabled":False,
            "promotions":sum(x["action"]=="promote" for x in markets.values())}
def main():
    data=ROOT/"data"
    report=json.loads((data/"ml-challenger-review.json").read_text())
    path=data/"ml-model-registry.json"
    registry=json.loads(path.read_text()) if path.exists() else {"schema_version":1,"markets":{},"deployable":{},"artifacts":{}}
    result=decide(report,registry)
    for market,decision in result["markets"].items():
        if decision["action"]=="promote":
            # Never change production registry from a research-only decision.
            # Deployment requires a separate, audited integration.
            raise RuntimeError("Research promotion cannot modify the production registry")
    (data/"ml-weekly-decisions.json").write_text(json.dumps(result,indent=2)+"\n")
    path.write_text(json.dumps(registry,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
