"""Research-only, chronological NFL weather-combination challenger.

Input: CSV of frozen pregame forecasts joined to verified final totals.
Never uses observed postgame weather as a forecast. No production changes.
"""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

FIELDS={"season","week","game_id","kickoff_utc","forecast_captured_at_utc","forecast_wind_mph","forecast_temp_f","forecast_precip_pct","roof_status","baseline_total","actual_total"}
def number(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except (TypeError,ValueError): return None
def timestamp(x):
    from datetime import datetime
    try:
        d=datetime.fromisoformat(str(x).replace("Z","+00:00"))
        return d if d.utcoffset() is not None else None
    except (TypeError,ValueError):return None
def feature(row):
    wind=number(row["forecast_wind_mph"]);temp=number(row["forecast_temp_f"]);rain=number(row["forecast_precip_pct"])
    if any(x is None for x in (wind,temp,rain)) or wind<0 or not -100<=temp<=140 or not 0<=rain<=100:
        return None
    if row["roof_status"].strip().lower() not in ("open","outdoor","closed","dome"):
        return None
    if row["roof_status"].strip().lower() in ("closed","dome"):
        return {"wind":False,"cold":False,"wet":False,"strong_wind":False}
    return {"wind":wind>=12,"cold":temp<=32,"wet":rain>=60,"strong_wind":wind>=18}
COMBOS={
    "wind_12":lambda f:f["wind"],
    "wind_18":lambda f:f["strong_wind"],
    "cold_only":lambda f:f["cold"],
    "wind_and_cold":lambda f:f["wind"] and f["cold"],
    "wind_and_wet":lambda f:f["wind"] and f["wet"],
    "cold_and_wet":lambda f:f["cold"] and f["wet"],
    "wind_cold_wet":lambda f:f["wind"] and f["cold"] and f["wet"],
}
def evaluate(path):
    with Path(path).open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        if not FIELDS.issubset(reader.fieldnames or []):raise ValueError("Missing required frozen forecast columns")
        rows=list(reader)
    seen=set();valid=[];rejected=defaultdict(int)
    for r in rows:
        try:
            key=(int(r["season"]),int(r["week"]),r["game_id"].strip())
            if not key[2]:raise ValueError()
        except (TypeError,ValueError):rejected["invalid_key"]+=1;continue
        if key in seen:raise ValueError("Duplicate game key: "+str(key))
        seen.add(key)
        kickoff=timestamp(r["kickoff_utc"]);captured=timestamp(r["forecast_captured_at_utc"])
        if not kickoff or not captured or captured>=kickoff:
            rejected["not_verified_pregame"]+=1;continue
        f=feature(r);baseline=number(r["baseline_total"]);actual=number(r["actual_total"])
        if f is None or baseline is None or actual is None or baseline<0 or actual<0:
            rejected["invalid_weather_or_score"]+=1;continue
        valid.append((key, f, baseline, actual))
    seasons=sorted({k[0] for k,_,_,_ in valid})
    if len(seasons)<2:
        return {"research_only":True,"production_changed":False,"eligible_for_promotion":False,
                "status":"insufficient_chronological_seasons","valid_rows":len(valid),"rejected":dict(rejected),"combinations":{}}
    holdout=seasons[-1];train=[x for x in valid if x[0][0]<holdout];test=[x for x in valid if x[0][0]==holdout]
    report={}
    for name,rule in COMBOS.items():
        tr=[(b,a) for _,f,b,a in train if rule(f)]
        ho=[(b,a) for _,f,b,a in test if rule(f)]
        if len(tr)<30 or len(ho)<20:
            report[name]={"status":"insufficient_samples","train_n":len(tr),"holdout_n":len(ho)}
            continue
        offset=sum(a-b for b,a in tr)/len(tr)
        offset=max(-6,min(6,offset))*len(tr)/(len(tr)+100)
        baseline_mae=sum(abs(a-b) for b,a in ho)/len(ho)
        challenger_mae=sum(abs(a-max(0,b+offset)) for b,a in ho)/len(ho)
        report[name]={"status":"holdout_evaluated","train_n":len(tr),"holdout_n":len(ho),
                      "frozen_offset":round(offset,3),"baseline_mae":round(baseline_mae,3),
                      "challenger_mae":round(challenger_mae,3),
                      "mae_improvement":round(baseline_mae-challenger_mae,3)}
    return {"research_only":True,"production_changed":False,"eligible_for_promotion":False,
            "status":"holdout_evaluated","train_seasons":seasons[:-1],"holdout_season":holdout,
            "valid_rows":len(valid),"rejected":dict(rejected),"combinations":report,
            "warning":"Multiple-combination screening is exploratory; requires independent confirmation, matching forecast provenance, and line-aware validation before promotion."}
def main():
    source=Path("data/backtests/weather-frozen-games.csv")
    if not source.exists():
        print("No timestamped, frozen weather backtest yet; no fabricated evaluation")
        return
    report=evaluate(source)
    Path("data/weather-combination-research.json").write_text(json.dumps(report,indent=2)+"\n")
    print(report["status"],report["valid_rows"])
if __name__=="__main__":main()
