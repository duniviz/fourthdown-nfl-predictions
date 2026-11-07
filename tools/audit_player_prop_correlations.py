"""Walk-forward QB/receiver and team rushing correlation research.

No projections are changed. Residuals are calculated against the existing
project_yards core using only previous player games. Correlations are descriptive
and are not validated betting probabilities.
"""
import argparse,json,math
from collections import defaultdict
from pathlib import Path
import nflreadpy as nfl
from live.player_research import project_yards,num

MARKETS={"passing_yards":"attempts","receiving_yards":"targets","rushing_yards":"carries"}
def corr(pairs):
    if len(pairs)<20:return None
    xs=[p[0] for p in pairs];ys=[p[1] for p in pairs]
    mx=sum(xs)/len(xs);my=sum(ys)/len(ys)
    xx=sum((x-mx)**2 for x in xs);yy=sum((y-my)**2 for y in ys)
    if xx<=0 or yy<=0:return None
    return round(sum((x-mx)*(y-my) for x,y in pairs)/math.sqrt(xx*yy),4)
def season_rows(season):
    weeks=defaultdict(list)
    for r in nfl.load_player_stats([season],summary_level="week").to_dicts():
        if str(r.get("season_type","REG")).upper() not in ("REG","2"):continue
        try:w=int(r["week"])
        except (TypeError,ValueError,KeyError):continue
        if 1<=w<=18 and r.get("team") and r.get("player_id"):weeks[w].append(r)
    history=defaultdict(list)
    residuals=[]
    for week in sorted(weeks):
        for r in weeks[week]:
            team=str(r["team"]);pid=str(r["player_id"])
            past=history[(team,pid)]
            if len(past)<3 or week-int(past[-1]["week"])>2:continue
            pos=str(r.get("position") or "").upper()
            for market,volume in MARKETS.items():
                if market=="passing_yards" and pos!="QB":continue
                if market=="receiving_yards" and pos not in ("WR","TE","RB"):continue
                if market=="rushing_yards" and pos not in ("RB","QB"):continue
                last=past[-5:]
                if sum(num(x.get(market)) for x in last)/len(last)<(85 if market=="passing_yards" else 18):continue
                pred,_,_,_=project_yards(past,market,volume)
                residuals.append({"season":season,"week":week,"team":team,"player_id":pid,
                                  "position":pos,"market":market,"residual":num(r.get(market))-pred})
        for r in weeks[week]:
            history[(str(r["team"]),str(r["player_id"]))].append(r)
    return residuals

def summarize(rows):
    groups=defaultdict(list)
    for r in rows:groups[(r["season"],r["week"],r["team"])].append(r)
    pairs=defaultdict(list)
    for group in groups.values():
        qbs=[r for r in group if r["market"]=="passing_yards" and r["position"]=="QB"]
        receivers=[r for r in group if r["market"]=="receiving_yards"]
        rushers=[r for r in group if r["market"]=="rushing_yards" and r["position"]=="RB"]
        if not qbs:continue
        qb=max(qbs,key=lambda r:r["residual"])
        for rec in receivers:
            pairs["qb_receiver"].append((qb["residual"],rec["residual"]))
            pairs["qb_wr" if rec["position"]=="WR" else "qb_te" if rec["position"]=="TE" else "qb_rb_receiver"].append((qb["residual"],rec["residual"]))
        for rb in rushers:pairs["qb_rb_rushing"].append((qb["residual"],rb["residual"]))
    return {k:{"samples":len(v),"residual_correlation":corr(v)} for k,v in sorted(pairs.items())}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",type=int,default=2016)
    p.add_argument("--end",type=int,default=2026)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    rows=[]
    for season in range(a.start,a.end+1):rows.extend(season_rows(season))
    train=[r for r in rows if r["season"]<=a.end-2]
    holdout=[r for r in rows if r["season"]>=a.end-1]
    report={"research_only":True,"production_changed":False,"prediction_cohort":"player-week with >=3 prior games",
        "training_seasons":[a.start,a.end-2],"holdout_seasons":[a.end-1,a.end],
        "training":summarize(train),"holdout":summarize(holdout),
        "by_season":{str(s):summarize([r for r in rows if r["season"]==s]) for s in range(a.start,a.end+1)},
        "approved_for_promotion":False,
        "limitations":["Residual correlations are descriptive, not a calibrated simulation or proof of improved prop accuracy",
                       "Quarterback selected by largest positive residual within team-week, not a pregame starter designation",
                       "Historical core predictions omit production role, weather and injury adjustments",
                       "No same-game sportsbook lines or frozen pregame shadow evaluation"]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"training":report["training"],"holdout":report["holdout"]},indent=2))
if __name__=="__main__":main()
