"""Deterministic broad V4 research search, selecting ONLY with 2024 data.
2025 is untouched holdout, not an optimization target. No live deployment.
"""
import json,random,math
from pathlib import Path
from live.backtest_players import backtest
MARKETS=("passing_yards","rushing_yards","receiving_yards")
SEED=20261029
TRIALS=600

def prediction(r,weights):
    u,d,interaction,curvature,old_blend=weights
    a=r["opportunity_signal"];b=r["defense_signal"]
    factor=max(0.7,min(1.3,1+u*a+d*b+interaction*a*b+curvature*a*abs(a)))
    return (1-old_blend)*r["new"]*factor+old_blend*r["old"]

def mae(rows,weights):
    return sum(abs(prediction(r,weights)-r["actual"]) for r in rows)/len(rows)

def main():
    rows=backtest()
    rng=random.Random(SEED)
    trials=[(0.,0.,0.,0.,0.)]
    for _ in range(TRIALS):
        trials.append(tuple(rng.choice(v) for v in (
            (-.5,-.3,-.15,0,.15,.3,.5),
            (-.5,-.3,-.15,0,.15,.3,.5),
            (-.8,-.4,0,.4,.8),
            (-.5,0,.5),
            (0,.1,.2,.3))))
    results=[]
    for market in MARKETS:
        train=[r for r in rows if r["season"]==2024 and r["market"]==market]
        test=[r for r in rows if r["season"]==2025 and r["market"]==market]
        if not train or not test:raise RuntimeError("Missing paired observations: "+market)
        ranked=sorted(trials,key=lambda w:(mae(train,w),sum(abs(v) for v in w)))
        winner=ranked[0]
        baseline=mae(test,trials[0]);challenger=mae(test,winner)
        results.append(dict(market=market,n_train=len(train),n_test=len(test),trials=len(trials),
          weights=list(winner),train_baseline_mae=round(mae(train,trials[0]),4),
          train_challenger_mae=round(mae(train,winner),4),
          baseline_mae=round(baseline,4),challenger_mae=round(challenger,4),
          holdout_improvement_pct=round(100*(baseline-challenger)/baseline,3),
          holdout_pass=challenger<baseline*.995))
    out=Path("research/v4-random-search");out.mkdir(parents=True,exist_ok=True)
    payload={"seed":SEED,"trials_per_market":len(trials),
      "selection":"All candidate rankings on 2024 only; single 2025 holdout evaluation",
      "scope":"Only existing pregame usage/defense signals, their interaction and incumbent/old blend. NOT new external NGS or coverage data.",
      "warning":"Repeated research across the same 2025 holdout eventually biases evaluation. Require fresh 2026 forward results before promotion.",
      "production":"Never automatically deploy", "results":results}
    (out/"results.json").write_text(json.dumps(payload,indent=2)+"\n")
    lines=["# V4 randomized research search","","2024 selects candidates; 2025 is evaluated once per run. No production promotion.","",
      "| Market | Trials | Baseline 2025 MAE | Challenger 2025 MAE | Change |",
      "|---|---:|---:|---:|---:|"]
    for r in results:
        lines.append(f'| {r["market"]} | {r["trials"]} | {r["baseline_mae"]:.3f} | {r["challenger_mae"]:.3f} | {r["holdout_improvement_pct"]:+.2f}% |')
    (out/"RESULTS.md").write_text("\n".join(lines)+"\n")
    print((out/"RESULTS.md").read_text())
if __name__=="__main__":main()
