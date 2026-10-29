"""Forward-era 2026 check of FROZEN 2024-selected V4 parameters.
Do not optimize on 2025 or 2026; require a production-equivalent replay before deployment.
"""
import json,random
from pathlib import Path
from live.backtest_players import backtest
from research.v4_random_search import SEED,TRIALS,MARKETS,mae

def main():
    # A fixed, reproducible candidate list and historical selection rule.
    rng=random.Random(SEED)
    candidates=[(0.,0.,0.,0.,0.)]
    for _ in range(TRIALS):
        candidates.append(tuple(rng.choice(v) for v in (
            (-.5,-.3,-.15,0,.15,.3,.5),
            (-.5,-.3,-.15,0,.15,.3,.5),
            (-.8,-.4,0,.4,.8),
            (-.5,0,.5),
            (0,.1,.2,.3))))
    rows=backtest(seasons=(2024,2026))
    results=[]
    for market in MARKETS:
        train=[r for r in rows if r["season"]==2024 and r["market"]==market]
        test=[r for r in rows if r["season"]==2026 and r["market"]==market]
        if not train or not test:raise RuntimeError("Missing historical or 2026 observations: "+market)
        weights=min(candidates,key=lambda w:(mae(train,w),sum(abs(v) for v in w)))
        baseline=mae(test,candidates[0]);challenger=mae(test,weights)
        improvement=100*(baseline-challenger)/baseline
        results.append(dict(market=market,train_n=len(train),test_n=len(test),
            evaluated_weeks=sorted(set(r["week"] for r in test)),frozen_weights=list(weights),
            baseline_mae=round(baseline,4),challenger_mae=round(challenger,4),
            improvement_pct=round(improvement,3),
            candidate_for_further_validation=improvement>=0.5))
    out=Path("research/v4-2026-validation");out.mkdir(parents=True,exist_ok=True)
    payload={"method":"2024 selection only; 2026 evaluation, no 2026 parameter fitting",
        "warning":"2026 may already have been informally inspected; not a pristine unseen holdout. Partial season and selected cohort.",
        "promotion":"NO AUTO PROMOTION. Requires production-equivalent paired replay, uncertainty analysis, 2026 week-by-week stability.",
        "results":results}
    (out/"results.json").write_text(json.dumps(payload,indent=2)+"\n")
    lines=["# Frozen V4 candidates on 2026 games","","Research only; parameters chosen exclusively on 2024. No live changes.","",
    "| Market | 2026 N | Baseline MAE | Challenger MAE | Change |",
    "|---|---:|---:|---:|---:|"]
    for r in results:
        lines.append(f'| {r["market"]} | {r["test_n"]} | {r["baseline_mae"]:.3f} | {r["challenger_mae"]:.3f} | {r["improvement_pct"]:+.2f}% |')
    (out/"RESULTS.md").write_text("\n".join(lines)+"\n")
    print((out/"RESULTS.md").read_text())
if __name__=="__main__":main()
