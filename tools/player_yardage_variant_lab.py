"""Chronological paired player-yardage parameter sweep; research only."""
import argparse,json
from collections import defaultdict
from pathlib import Path
import nflreadpy as nfl
from live.player_research import num,PRIOR_RATE,PRIOR_OPPORTUNITIES
from live.backtest_players import backtest

MARKETS={"passing_yards":"attempts","rushing_yards":"carries","receiving_yards":"targets"}
VARIANTS={
 "live_core":(.88,.65,1.0,.80),
 "recent_heavy":(.78,.80,1.0,.80),
 "recent_light":(.94,.50,1.0,.80),
 "less_prior":(.88,.65,.50,.80),
 "more_prior":(.88,.65,1.50,.80),
 "less_shrink":(.88,.65,1.0,.90),
 "more_shrink":(.88,.65,1.0,.65),
 "recent_heavy_less_prior":(.78,.80,.50,.90),
 "recent_light_more_prior":(.94,.50,1.50,.65),
}
def forecast(past,market,volume,params):
    decay,recent_mix,prior_scale,rate_mix=params
    recent=past[-8:]
    weights=[decay**(len(recent)-1-i) for i in range(len(recent))]
    weighted_volume=sum(w*max(0,num(r.get(volume))) for w,r in zip(weights,recent))/sum(weights)
    total_opp=sum(w*max(0,num(r.get(volume))) for w,r in zip(weights,recent))
    total_yards=sum(w*max(0,num(r.get(market))) for w,r in zip(weights,recent))
    prior=PRIOR_OPPORTUNITIES[market]*prior_scale
    rate=(total_yards+PRIOR_RATE[market]*prior)/(total_opp+prior)
    season_volume=sum(max(0,num(r.get(volume))) for r in past)/len(past)
    expected=recent_mix*weighted_volume+(1-recent_mix)*season_volume
    season_yards=sum(max(0,num(r.get(market))) for r in past)/len(past)
    return max(0,rate_mix*expected*rate+(1-rate_mix)*season_yards)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",type=int,default=2016)
    p.add_argument("--end",type=int,default=2026)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    seasons=range(a.start,a.end+1)
    histories=defaultdict(list)
    for season in seasons:
        for row in nfl.load_player_stats([season],summary_level="week").to_dicts():
            if str(row.get("season_type","REG")).upper() not in ("REG","2"):continue
            try:w=int(row["week"])
            except (TypeError,ValueError,KeyError):continue
            if 1<=w<=18 and row.get("team") and row.get("player_id"):
                histories[(season,str(row["team"]),str(row["player_id"]))].append(row)
    for rows in histories.values():rows.sort(key=lambda r:int(r["week"]))
    # Match the existing challenger cohort exactly, no future rows in predictions.
    paired=backtest(tuple(seasons))
    errors=defaultdict(list)
    for r in paired:
        market=r["market"]
        if market not in MARKETS:continue
        hist=histories[(r["season"],r["team"],r["player_id"])]
        past=[x for x in hist if int(x["week"])<r["week"]]
        if len(past)<3:continue
        actual=r["actual"]
        for name,params in VARIANTS.items():
            pred=forecast(past,market,MARKETS[market],params)
            errors[(market,name,r["season"])].append(abs(pred-actual))
        errors[(market,"previous_challenger",r["season"])].append(abs(r["new"]-actual))
    report={"scope":"shared live yardage core and historical challenger; not full production replay","production_changed":False,"markets":{}}
    for market in MARKETS:
        rows={}
        for name in list(VARIANTS)+["previous_challenger"]:
            season_metrics={}
            all_errors=[]
            for season in seasons:
                values=errors[(market,name,season)]
                if values:
                    season_metrics[str(season)]={"n":len(values),"mae":round(sum(values)/len(values),3)}
                    all_errors+=values
            rows[name]={"samples":len(all_errors),"mae":round(sum(all_errors)/len(all_errors),3) if all_errors else None,"by_season":season_metrics}
        baseline=rows["live_core"]["mae"]
        for name,v in rows.items():
            v["improvement_vs_live_pct"]=round(100*(baseline-v["mae"])/baseline,2) if baseline and v["mae"] is not None else None
        # Hold out the two latest seasons from variant selection to avoid choosing on test data.
        training=[s for s in seasons if s<a.end-1]
        holdout=[s for s in seasons if s>=a.end-1]
        def score(name,ss):
            vals=[x for s in ss for x in errors[(market,name,s)]]
            return sum(vals)/len(vals) if vals else float("inf")
        winner=min(VARIANTS,key=lambda name:score(name,training))
        holdout_live=score("live_core",holdout);holdout_candidate=score(winner,holdout)
        report["markets"][market]={"variants":rows,"training_selected":winner,
            "holdout_seasons":list(holdout),"holdout_live_mae":round(holdout_live,3),
            "holdout_selected_mae":round(holdout_candidate,3),
            "holdout_improvement_pct":round(100*(holdout_live-holdout_candidate)/holdout_live,2) if holdout_live else None,
            "approved_for_promotion":False}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({m:{"selected":v["training_selected"],"holdout_improvement_pct":v["holdout_improvement_pct"],"live_mae":v["variants"]["live_core"]["mae"]} for m,v in report["markets"].items()},indent=2))
if __name__=="__main__":main()
