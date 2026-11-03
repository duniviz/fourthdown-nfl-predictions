"""Chronological residual-bias challenger trained on historical forecasts only.

The historical old/new labels are not guaranteed to match today's production model.
This is research only and cannot approve or alter production predictions.
"""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

def finite(v):
    try:
        n=float(v)
        return n if math.isfinite(n) else None
    except (TypeError,ValueError):
        return None

def evaluate(path):
    with Path(path).open(newline="",encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    required={"season","week","player_id","market","actual","old","new"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Missing historical challenger fields")
    cleaned=[]
    seen=set()
    for row in rows:
        try:
            season=int(row["season"]);week=int(row["week"])
        except (TypeError,ValueError):
            continue
        actual,old,new=(finite(row.get(k)) for k in ("actual","old","new"))
        if min(season,week)<1 or actual is None or old is None or new is None or not row["player_id"] or not row["market"]:
            continue
        key=(season,week,row["player_id"],row["market"])
        if key in seen:
            raise ValueError("Duplicate historical row: "+repr(key))
        seen.add(key)
        cleaned.append((season,week,row["market"],actual,old,new))
    seasons=sorted({r[0] for r in cleaned})
    if len(seasons)<2:
        raise ValueError("At least two chronological seasons required")
    holdout=seasons[-1]
    training=defaultdict(list)
    testing=defaultdict(list)
    for season,week,market,actual,old,new in cleaned:
        (training if season<holdout else testing)[market].append((week,actual,old,new))
    result={}
    for market,hold in sorted(testing.items()):
        train=training.get(market,[])
        if len(train)<30 or len(hold)<30:
            result[market]={"status":"insufficient_training_or_holdout","train_n":len(train),"holdout_n":len(hold)}
            continue
        # One pre-registered, shrunk market-level residual correction, frozen before holdout.
        residual=sum(a-p for _,a,_,p in train)/len(train)
        offset=residual*len(train)/(len(train)+100)
        baseline=sum(abs(a-p) for _,a,_,p in hold)/len(hold)
        challenger=sum(abs(a-max(0,p+offset)) for _,a,_,p in hold)/len(hold)
        weekly=defaultdict(list)
        for week,a,_,p in hold:
            weekly[week].append((abs(a-p),abs(a-max(0,p+offset))))
        week_metrics=[{"week":w,"samples":len(v),"reference_mae":round(sum(x for x,_ in v)/len(v),3),"challenger_mae":round(sum(y for _,y in v)/len(v),3)} for w,v in sorted(weekly.items())]
        weeks_improved=sum(w["challenger_mae"]<w["reference_mae"] for w in week_metrics)
        result[market]={"status":"holdout_evaluated","train_n":len(train),"holdout_n":len(hold),
            "frozen_offset":round(offset,3),"historical_new_mae":round(baseline,3),
            "bias_challenger_mae":round(challenger,3),
            "mae_delta":round(baseline-challenger,3),"holdout_weeks":len(week_metrics),
            "weeks_improved":weeks_improved,"weekly_diagnostics":week_metrics,
            "eligible_for_promotion":False}
    return {"research_only":True,"production_changed":False,"automatic_promotion":False,
            "production_equivalence_verified":False,"historical_train_seasons":seasons[:-1],
            "holdout_season":holdout,"markets":result,
            "warning":"Historical new is not verified as current production. This is a single frozen holdout, not a live-model promotion test."}

def main():
    report=evaluate("data/backtests/player-predictions.csv")
    dest=Path("data/research-bias-challenger.json")
    dest.write_text(json.dumps(report,indent=2)+"\n")
    print("Research-only challenger evaluated",len(report["markets"]),"markets")
if __name__=="__main__":
    main()
