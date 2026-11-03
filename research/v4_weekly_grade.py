"""Weekly paired grading of frozen research candidates vs actual completed 2026 games.
Historical replays are diagnostic, NOT archived pregame predictions. Never auto-promote.
"""
import csv,json,random
from pathlib import Path
from collections import defaultdict
from live.backtest_players import backtest
from research.v4_random_search import SEED,TRIALS,MARKETS,prediction

def candidates():
    rng=random.Random(SEED)
    weights=[(0.,0.,0.,0.,0.)]
    for _ in range(TRIALS):
        weights.append(tuple(rng.choice(v) for v in (
            (-.5,-.3,-.15,0,.15,.3,.5),
            (-.5,-.3,-.15,0,.15,.3,.5),
            (-.8,-.4,0,.4,.8),
            (-.5,0,.5),
            (0,.1,.2,.3))))
    return weights

def main():
    rows=backtest(seasons=(2024,2026))
    pool=candidates()
    winners={}
    for market in MARKETS:
        train=[r for r in rows if r["season"]==2024 and r["market"]==market]
        if not train:raise RuntimeError("Missing 2024 training observations: "+market)
        winners[market]=min(pool,key=lambda w:(sum(abs(prediction(r,w)-r["actual"]) for r in train)/len(train),sum(abs(v) for v in w)))
    actual=[r for r in rows if r["season"]==2026]
    if not actual:raise RuntimeError("No completed 2026 player observations")
    by_week=defaultdict(list)
    for r in actual:by_week[(r["week"],r["market"])].append(r)
    report=[]
    for (week,market),games in sorted(by_week.items()):
        weights=winners[market]
        baseline=sum(abs(r["new"]-r["actual"]) for r in games)/len(games)
        challenger=sum(abs(prediction(r,weights)-r["actual"]) for r in games)/len(games)
        report.append(dict(week=week,market=market,n=len(games),baseline_mae=round(baseline,3),
            challenger_mae=round(challenger,3),improvement_pct=round(100*(baseline-challenger)/baseline,3) if baseline else 0))
    out=Path("research/v4-weekly-results");out.mkdir(parents=True,exist_ok=True)
    with (out/"weekly.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(report[0]));writer.writeheader();writer.writerows(report)
    (out/"results.json").write_text(json.dumps({"method":"Frozen 2024-selected challengers, 2026 weekly completed-game replay",
      "warning":"This is a historical walk-forward replay, not a timestamped archive of actual pregame predictions. Do not infer live forecast performance.",
      "results":report},indent=2)+"\n")
    lines=["# Weekly V4 research vs actual NFL results","","**Historical walk-forward replay, not archived pregame forecasts. No automatic promotion.**","",
    "| Week | Market | Players | Baseline MAE | Challenger MAE | Change |",
    "|---:|---|---:|---:|---:|---:|"]
    for r in report:
        lines.append(f'| {r["week"]} | {r["market"]} | {r["n"]} | {r["baseline_mae"]:.3f} | {r["challenger_mae"]:.3f} | {r["improvement_pct"]:+.2f}% |')
    (out/"RESULTS.md").write_text("\n".join(lines)+"\n")
    print((out/"RESULTS.md").read_text())
if __name__=="__main__":main()
