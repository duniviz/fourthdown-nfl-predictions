#!/usr/bin/env python3
"""Conservative research sorting; never interpret raw yardage gaps as bet confidence."""
import argparse,json,math
from datetime import datetime,timezone
from pathlib import Path

def evaluate(report,now=None,calibration=None):
    now=now or datetime.now(timezone.utc)
    results=[]
    for row in report.get("comparisons",[]):
        r=dict(row)
        reasons=[]
        if r.get("match_status")!="matched": reasons.append("no_unambiguous_current_line")
        if not r.get("recommendation_eligible",False): reasons.append("availability_not_verified")
        if r.get("availability_status") not in ("active","probable"): reasons.append("game_day_status_not_confirmed")
        try:
            line=float(r.get("dk_line"))
            projected=float(r.get("projected_yards"))
            if not all(map(math.isfinite,(line,projected))) or line<=0: raise ValueError
        except (TypeError,ValueError):
            reasons.append("invalid_line_or_projection");line=projected=None
        try:
            quote=datetime.fromisoformat(str(r.get("last_update")).replace("Z","+00:00")).astimezone(timezone.utc)
            age=(now-quote).total_seconds()/3600
            if not 0<=age<=3: reasons.append("quote_not_fresh")
        except (TypeError,ValueError):
            reasons.append("quote_timestamp_invalid")
        gap=round(projected-line,1) if line is not None else None
        relative=round(100*abs(gap)/line,1) if gap is not None else None
        market_cal=(calibration or {}).get("markets",{}).get(r.get("market"),{})
        residuals=market_cal.get("residuals_yards",[]) if market_cal.get("status")=="validated_research_distribution" else []
        empirical_over=None
        interval=None
        if not reasons and residuals and line is not None:
            empirical_over=round(sum(projected+e>line for e in residuals)/len(residuals),3)
            bounds=market_cal["interval_80_residual_yards"]
            interval=[round(projected+b,1) for b in bounds]
        r.update({"research_over_probability":empirical_over,"research_interval_80_yards":interval,"research_difference_yards":gap,"relative_difference_pct":relative,"ranking_status":"eligible_for_further_validation" if not reasons else "blocked","block_reasons":reasons,"calibrated_probability":None,"confidence_score":None})
        results.append(r)
    # Eligible rows are not betting recommendations; without historical calibration no ranked picks.
    eligible=sum(x["ranking_status"]=="eligible_for_further_validation" for x in results)
    return {"status":"research_only_no_bet_ranking","season":report.get("season"),"week":report.get("week"),"generated_at_utc":now.isoformat(),"counts":{"total":len(results),"eligible_for_further_validation":eligible,"blocked":len(results)-eligible},"note":"Raw model-vs-book gaps are NOT probabilities or confidence. No bet ranking is produced without out-of-sample calibration and verified availability.","comparisons":results}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--comparisons-json",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--calibration-json",type=Path)
    a=p.parse_args()
    calibration=json.loads(a.calibration_json.read_text()) if a.calibration_json and a.calibration_json.exists() else None
    output=evaluate(json.loads(a.comparisons_json.read_text()),calibration=calibration)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(output,indent=2)+"\n")
    print("Prop research eligibility:",output["counts"],"; no uncalibrated bet ranking")
if __name__=="__main__":main()
