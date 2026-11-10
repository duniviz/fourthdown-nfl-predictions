#!/usr/bin/env python3
"""Leakage-aware research challengers on retrospective walk-forward player projections.

Features are restricted to historical walk-forward estimates and known identifiers;
no actuals, errors, or same-game postgame stats are inputs.
Train on earlier seasons, evaluate untouched latest season.
"""
import argparse,csv,json,math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestRegressor,HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"data/backtests/player-predictions.csv"
DEST=ROOT/"data/ml-challenger-review.json"
MIN_TRAIN=100
MIN_TEST=30

def load(path):
    with path.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
    seen=set();out=[]
    for r in rows:
        try:
            season,week=int(r["season"]),int(r["week"])
            actual,base=float(r["actual"]),float(r["new"])
            old=float(r["old"])
            if not all(math.isfinite(x) for x in (actual,base,old)) or min(actual,base,old)<0:continue
            key=(season,week,r["player_id"],r["market"])
            if key in seen:raise ValueError("Duplicate pregame row: "+str(key))
            seen.add(key)
            # No contemporaneous actual, errors, or future performance features.
            out.append({"season":season,"week":week,"market":r["market"],
                        "features":[base,old,week],"actual":actual,"baseline":base})
        except (KeyError,TypeError):continue
    return out

def walkforward_split(items, holdout, week):
    """Only earlier weeks and seasons may train a target-week forecast."""
    return ([r for r in items if (r["season"], r["week"]) < (holdout, week)],
            [r for r in items if r["season"] == holdout and r["week"] == week])


def evaluate(rows):
    seasons=sorted({r["season"] for r in rows})
    if len(seasons)<2:return {"status":"insufficient_seasons","markets":{}}
    holdout=seasons[-1]
    groups=defaultdict(list)
    for r in rows:groups[r["market"]].append(r)
    report={}
    for market,items in sorted(groups.items()):
        weeks=sorted({r["week"] for r in items if r["season"]==holdout})
        scored=[]
        previous_weeks=set()
        for week in weeks:
            train,test=walkforward_split(items,holdout,week)
            if len(train)<MIN_TRAIN or not test: continue
            x=np.asarray([r["features"] for r in train],dtype=float)
            y=np.asarray([r["actual"] for r in train],dtype=float)
            xt=np.asarray([r["features"] for r in test],dtype=float)
            models={
                "ridge":make_pipeline(StandardScaler(),Ridge(alpha=100.0)),
                "random_forest":RandomForestRegressor(n_estimators=100,max_depth=5,min_samples_leaf=15,random_state=42,n_jobs=1),
                "gradient_boosting":HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=9,min_samples_leaf=25,l2_regularization=20,random_state=42)
            }
            predictions={}
            for name,model in models.items():
                model.fit(x,y)
                predictions[name]=np.maximum(0,model.predict(xt))
            for i,r in enumerate(test):
                scored.append({"actual":r["actual"],"baseline":r["baseline"],
                               **{name:float(p[i]) for name,p in predictions.items()}})
            previous_weeks.update(r["week"] for r in train if r["season"]==holdout)
        if len(scored)<MIN_TEST:
            report[market]={"status":"insufficient_samples","holdout":len(scored)}
            continue
        baseline=float(np.mean([abs(r["actual"]-r["baseline"]) for r in scored]))
        scores={}
        for name in ("ridge","random_forest","gradient_boosting"):
            mae=float(np.mean([abs(r["actual"]-r[name]) for r in scored]))
            scores[name]={"mae":round(mae,3),"improvement_vs_baseline":round(baseline-mae,3),"beats_baseline":mae<baseline}
        report[market]={"status":"evaluated","holdout":len(scored),"baseline_mae":round(baseline,3),
                        "current_season_training_weeks":sorted(previous_weeks),"challengers":scores}
    return {"status":"evaluated","holdout_season":holdout,"training_seasons":seasons[:-1],
            "evaluation":"week-blocked walk-forward; previous completed current-season weeks are added before each target week",
            "markets":report}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=SOURCE)
    args=parser.parse_args()
    result=evaluate(load(args.input))
    result.update({"generated_at_utc":datetime.now(timezone.utc).isoformat(),
                   "research_only":True,"production_changed":False,"automatic_promotion":False,
                   "feature_policy":"retrospective walk-forward player estimates + week; no outcomes as features",
                   "limitation":"Retrospective walk-forward backtest, not live frozen predictions; no ATS, winners, weather or DK lines in source.",
                   "source_file":str(args.input)})
    DEST.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"markets":result["markets"]},indent=2))
if __name__=="__main__":main()
