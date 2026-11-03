#!/usr/bin/env python3
"""Walk-forward empirical residual calibration with chronological validation.
Never claim DraftKings betting profitability or certify player availability.
"""
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path
from project_player_yards import project,FIELDS

def percentile(values,q):
    a=sorted(values)
    if not a:return None
    k=(len(a)-1)*q
    lo=int(k);hi=min(lo+1,len(a)-1)
    return a[lo]*(1-(k-lo))+a[hi]*(k-lo)

def build(rows,season,last_week,min_train=30,min_holdout=15):
    actual=defaultdict(list)
    for r in rows:
        try:
            if int(r["season"])!=season or r.get("season_type","REG")!="REG":continue
            w=int(r["week"]);pid=r.get("player_id") or r.get("gsis_id")
            if not pid or w>last_week:continue
            for market in FIELDS:
                y=float(r[market])
                if math.isfinite(y) and 0<=y<=700:actual[(w,pid,market)].append(y)
        except (KeyError,ValueError,TypeError):continue
    samples=defaultdict(list)
    for week in range(4,last_week+1):
        for p in project(rows,season,week):
            ys=actual.get((week,p["player_id"],p["market"]))
            if not ys or len(ys)!=1:continue
            if p["latest_week_used"]>=week:raise ValueError("future information leaked")
            # actual minus forecast, used to estimate distribution of outcomes
            samples[p["market"]].append((week,ys[0]-float(p["projected_yards"])))
    markets={}
    for market,records in samples.items():
        records.sort()
        weeks=sorted(set(w for w,_ in records))
        if len(weeks)<2:
            markets[market]={"status":"insufficient_validation_weeks","samples":len(records)};continue
        holdout_week=weeks[-1]
        train=[e for w,e in records if w<holdout_week]
        holdout=[e for w,e in records if w==holdout_week]
        if len(train)<min_train or len(holdout)<min_holdout:
            markets[market]={"status":"insufficient_validation_samples","train_samples":len(train),"holdout_samples":len(holdout),"holdout_week":holdout_week};continue
        lo=percentile(train,.1);hi=percentile(train,.9)
        coverage=sum(lo<=e<=hi for e in holdout)/len(holdout)
        # Evaluate CDF predictions at synthetic offsets, not historical sportsbook prices.
        thresholds=(-20,0,20)
        predictions=[(sum(e>offset for e in train)/len(train),int(e>offset)) for e in holdout for offset in thresholds]
        brier=sum((p-y)**2 for p,y in predictions)/len(predictions)
        base=sum(y for _,y in predictions)/len(predictions)
        baseline=sum((base-y)**2 for _,y in predictions)/len(predictions)
        # Only publish probability estimates when validation does not underperform naive baseline.
        passed=coverage>=.65 and brier<=baseline
        markets[market]={"status":"validated_research_distribution" if passed else "validation_failed","train_samples":len(train),"holdout_samples":len(holdout),"holdout_week":holdout_week,"interval_80_residual_yards":[round(lo,2),round(hi,2)],"holdout_interval_coverage":round(coverage,3),"holdout_brier":round(brier,4),"holdout_baseline_brier":round(baseline,4),"residuals_yards":[round(e,2) for e in train] if passed else [],"note":"Holdout validation uses synthetic projection-relative thresholds, NOT historical DK lines."}
    return {"status":"research_only_chronological_holdout","season":season,"through_week":last_week,"markets":markets,"note":"Empirical probabilities describe historical outcome residuals, not independently calibrated sportsbook betting edges; no automatic bet ranking."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--weekly-csv",type=Path,required=True)
    p.add_argument("--season",type=int,required=True)
    p.add_argument("--through-week",type=int,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    with a.weekly_csv.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
    result=build(rows,a.season,a.through_week)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print("Chronological calibration validation:",{k:{x:v.get(x) for x in ("status","train_samples","holdout_samples","holdout_interval_coverage","holdout_brier")} for k,v in result["markets"].items()})
if __name__=="__main__":main()
