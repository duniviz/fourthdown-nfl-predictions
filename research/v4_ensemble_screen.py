"""Walk-forward paired V4 ensemble screening. 2024 selects weight; 2025 is untouched holdout.
This is a low-risk first challenger, not evidence of new advanced feature improvement.
"""
import json
from pathlib import Path
from collections import defaultdict
from live.backtest_players import backtest

WEIGHTS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)
MARKETS = ("passing_yards", "rushing_yards", "receiving_yards")

def mae(rows, weight):
    return sum(abs((1-weight)*float(r["new"])+weight*float(r["old"])-float(r["actual"])) for r in rows)/len(rows)

def main():
    data=backtest()
    results=[]
    for market in MARKETS:
        train=[r for r in data if r["season"]==2024 and r["market"]==market]
        holdout=[r for r in data if r["season"]==2025 and r["market"]==market]
        if not train or not holdout: raise RuntimeError("Missing paired market/season data: "+market)
        weight=min(WEIGHTS,key=lambda w:mae(train,w))
        baseline=mae(holdout,0.0)
        challenger=mae(holdout,weight)
        improvement=100*(baseline-challenger)/baseline
        results.append({"market":market,"train_n":len(train),"holdout_n":len(holdout),
                        "old_model_blend_weight":weight,"baseline_mae":round(baseline,4),
                        "challenger_mae":round(challenger,4),"improvement_pct":round(improvement,3),
                        "beats_baseline":improvement>0.5})
    out=Path("research/v4-screening")
    out.mkdir(parents=True,exist_ok=True)
    payload={"method":"2024 weight selection / 2025 holdout; same player-week rows; no 2025 tuning",
             "promotion":"NOT AUTOMATIC: require production-equivalent replay, more seasons and calibration",
             "results":results}
    (out/"results.json").write_text(json.dumps(payload,indent=2)+"\n")
    lines=["# V4 ensemble screening","","2024 selects the weight, 2025 tests it. Research only.","",
           "| Market | 2025 N | Old-model blend | Live-model MAE | Challenger MAE | Change |",
           "|---|---:|---:|---:|---:|---:|"]
    for r in results:
        lines.append(f'| {r["market"]} | {r["holdout_n"]} | {r["old_model_blend_weight"]:.0%} | {r["baseline_mae"]:.3f} | {r["challenger_mae"]:.3f} | {r["improvement_pct"]:+.2f}% |')
    (out/"RESULTS.md").write_text("\n".join(lines)+"\n")
    print((out/"RESULTS.md").read_text())
if __name__=="__main__":main()
