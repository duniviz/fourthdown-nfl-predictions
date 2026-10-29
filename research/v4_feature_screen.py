"""V4 usage and defensive-strength challengers. No live deployment.
Only 2024 chooses coefficients; 2025 is an untouched paired holdout.
"""
import json
from pathlib import Path
from live.backtest_players import backtest

MARKETS=("passing_yards","rushing_yards","receiving_yards")
# Explicit simple grid: incumbent is included; 2025 cannot select coefficients.
COEFFICIENTS=(0.0,0.1,0.2,0.35,0.5,-0.1,-0.2)
def forecast(row, usage, defense):
    factor=max(0.7,min(1.3,1+usage*row["opportunity_signal"]+defense*row["defense_signal"]))
    return row["new"]*factor

def mae(rows, usage, defense):
    return sum(abs(forecast(r,usage,defense)-r["actual"]) for r in rows)/len(rows)

def main():
    rows=backtest()
    results=[]
    for market in MARKETS:
        train=[r for r in rows if r["season"]==2024 and r["market"]==market]
        holdout=[r for r in rows if r["season"]==2025 and r["market"]==market]
        if not train or not holdout: raise RuntimeError("Missing season or market: "+market)
        candidates=[(u,d) for u in COEFFICIENTS for d in COEFFICIENTS]
        # Favor simpler coefficients in case of a tie.
        usage,defense=min(candidates,key=lambda pair:(mae(train,*pair),abs(pair[0])+abs(pair[1])))
        baseline=mae(holdout,0,0)
        tested=mae(holdout,usage,defense)
        improvement=100*(baseline-tested)/baseline
        results.append(dict(market=market,n_2024=len(train),n_2025=len(holdout),
            usage_coefficient=usage,defense_coefficient=defense,
            baseline_mae=round(baseline,4),challenger_mae=round(tested,4),
            improvement_pct=round(improvement,3),
            research_pass=improvement>=0.5))
    out=Path("research/v4-feature-screening");out.mkdir(parents=True,exist_ok=True)
    payload={"design":"2024 coefficient selection, 2025 holdout; same player-week rows",
      "scope":"Historical opportunity trend and opponent defensive allowance signals only. NGS, coverage, pressure and full production replay NOT included.",
      "deployment":"Never automatically deploy; needs live-equivalent replay and additional validation",
      "results":results}
    (out/"results.json").write_text(json.dumps(payload,indent=2)+"\n")
    lines=["# V4 usage and defense feature screening","","2024 trains, 2025 evaluates. Research only.","",
    "| Market | 2025 N | Usage coefficient | Defense coefficient | Baseline MAE | Challenger MAE | Improvement |",
    "|---|---:|---:|---:|---:|---:|---:|"]
    for r in results:
        lines.append(f'| {r["market"]} | {r["n_2025"]} | {r["usage_coefficient"]:+.2f} | {r["defense_coefficient"]:+.2f} | {r["baseline_mae"]:.3f} | {r["challenger_mae"]:.3f} | {r["improvement_pct"]:+.2f}% |')
    (out/"RESULTS.md").write_text("\n".join(lines)+"\n")
    print((out/"RESULTS.md").read_text())
if __name__=="__main__":main()
