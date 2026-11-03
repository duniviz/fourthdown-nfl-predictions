#!/usr/bin/env python3
"""FOURTHDOWN Accuracy Engine: chronological research, no production writes.

Historical CSV contains model-vs-actual forecasts, not historical sportsbook lines.
Therefore all probability diagnostics below use synthetic thresholds and MUST NOT
be presented as calibrated DraftKings over/under confidence.
"""
import csv, json, math, argparse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

def mean(xs):
    return sum(xs)/len(xs) if xs else None

def metrics(rows, field):
    if not rows:return {"samples":0}
    errs=[float(r[field])-float(r["actual"]) for r in rows]
    return {"samples":len(errs),"mae":round(mean([abs(e) for e in errs]),3),
            "rmse":round(math.sqrt(mean([e*e for e in errs])),3),
            "bias":round(mean(errs),3)}

def run(path):
    with path.open(newline="",encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    required={"season","week","player_id","team","market","actual","old","new"}
    if not rows or not required.issubset(rows[0]):raise ValueError("Missing historical backtest columns")
    valid=[]
    seen=set()
    for r in rows:
        try:
            if not all(math.isfinite(float(r[k])) for k in ("actual","old","new")):continue
            r["season"]=int(r["season"]);r["week"]=int(r["week"])
            if r["week"]<1 or not r["player_id"]:continue
            key=(r["season"],r["week"],r["player_id"],r["market"])
            if key in seen:raise ValueError(f"Duplicate historical prediction: {key}")
            seen.add(key)
            valid.append(r)
        except (ValueError,TypeError,KeyError):continue
    if not valid:raise ValueError("No valid backtest samples")
    if len({r["season"] for r in valid})<2:raise ValueError("Need at least two chronological seasons for holdout")
    # The final chronological season is the untouched reporting holdout.
    seasons=sorted({r["season"] for r in valid})
    holdout_season=seasons[-1]
    holdout=[r for r in valid if r["season"]==holdout_season]
    train=[r for r in valid if r["season"]<holdout_season]
    by_market=defaultdict(list)
    for r in holdout:by_market[r["market"]].append(r)
    markets={}
    for market,items in sorted(by_market.items()):
        champion=metrics(items,"old")
        challenger=metrics(items,"new")
        # Research-only: historical labels are not evidence of current production version.
        improvement=round(champion["mae"]-challenger["mae"],3)
        groups=defaultdict(list)
        for r in items:
            groups[("team",r["team"])].append(r)
            groups[("week",str(r["week"]))].append(r)
        weak=[]
        for (dimension,value),subset in groups.items():
            if len(subset)<12:continue
            m=metrics(subset,"new")
            weak.append({"dimension":dimension,"value":value,**m})
        weak.sort(key=lambda x:x["mae"],reverse=True)
        # A model challenger cannot be promoted on a single holdout improvement.
        markets[market]={"reference_baseline":champion,"research_challenger":challenger,
          "holdout_mae_improvement":improvement,"challenger_better_on_holdout":improvement>0,
          "eligible_for_promotion":False,"weak_spots":weak[:12]}
    # Chronological synthetic-threshold reliability experiment; never DK confidence.
    probability={}
    for market in sorted(by_market):
        training=[r for r in train if r["market"]==market]
        testing=by_market[market]
        if len(training)<100 or len(testing)<30:
            probability[market]={"status":"insufficient_data","training_samples":len(training),"holdout_samples":len(testing),"dk_calibrated":False}
            continue
        residuals=[float(r["actual"])-float(r["new"]) for r in training]
        forecasts=[]
        for r in testing:
            for offset in (-10,0,10):
                prob=sum(e>offset for e in residuals)/len(residuals)
                actual=int(float(r["actual"])>float(r["new"])+offset)
                forecasts.append((prob,actual))
        brier=mean([(p-y)**2 for p,y in forecasts])
        base=mean([y for _,y in forecasts])
        base_brier=mean([(base-y)**2 for _,y in forecasts])
        probability[market]={"status":"research_only_synthetic_thresholds",
          "training_samples":len(training),"holdout_samples":len(testing),
          "brier":round(brier,4),"naive_baseline_brier":round(base_brier,4),
          "beats_naive_baseline":brier<base_brier,"dk_calibrated":False,
          "publish_as_player_confidence":False}
    return {"generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "status":"research_only","production_changed":False,"automatic_promotion":False,
      "holdout_season":holdout_season,"training_seasons":seasons[:-1],
      "historical_rows":len(valid),"holdout_rows":len(holdout),
      "markets":markets,"probability_research":probability,
      "note":"Backtest old/new are historical comparison columns, not proven current production/challenger identities. No historical DK lines in this CSV; no sportsbook probabilities certified."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path("data/backtests/player-predictions.csv"))
    p.add_argument("--output",type=Path,default=Path("data/accuracy-engine.json"))
    a=p.parse_args()
    result=run(a.input)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print("Accuracy Engine:",result["holdout_rows"],"holdout rows,",len(result["markets"]),"markets; production unchanged")

if __name__=="__main__":main()
