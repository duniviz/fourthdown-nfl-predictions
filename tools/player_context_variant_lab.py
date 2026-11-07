"""Walk-forward team workload and defensive matchup yardage experiments.

All features are constructed from completed prior weeks. Historical player-week
cohorts are identical across candidates. No production deployment.
"""
import argparse,json
from collections import defaultdict
from pathlib import Path
import nflreadpy as nfl
from live.player_research import METRICS,num,project_yards

MARKETS={"passing_yards":"attempts","rushing_yards":"carries","receiving_yards":"targets"}
VARIANTS={
 "live_core":(0.0,0.0,0.0),
 "workload_25":(.25,0.0,0.0),
 "workload_50":(.50,0.0,0.0),
 "workload_75":(.75,0.0,0.0),
 "defense_5":(0.0,.05,0.0),
 "defense_10":(0.0,.10,0.0),
 "position_defense_5":(0.0,0.0,.05),
 "position_defense_10":(0.0,0.0,.10),
 "workload_25_defense_5":(.25,.05,0.0),
 "workload_50_defense_5":(.50,.05,0.0),
 "workload_25_position_5":(.25,0.0,.05),
 "workload_50_position_5":(.50,0.0,.05),
}
def load_season(season):
    weeks=defaultdict(list)
    for r in nfl.load_player_stats([season],summary_level="week").to_dicts():
        if str(r.get("season_type","REG")).upper() not in ("REG","2"):continue
        try:w=int(r["week"])
        except (ValueError,TypeError,KeyError):continue
        if 1<=w<=18 and r.get("team") and r.get("player_id"):weeks[w].append(r)
    return weeks

def predictions(weeks,season):
    history=defaultdict(list)
    output=[]
    for week in sorted(weeks):
        if week>=4:
            team_week=defaultdict(lambda:defaultdict(float))
            allowed=defaultdict(lambda:defaultdict(float))
            pos_allowed=defaultdict(lambda:defaultdict(float))
            for (team,pid),past in history.items():
                for r in past:
                    w=int(r["week"]);opp=str(r.get("opponent_team") or "")
                    for vol in set(MARKETS.values()):
                        team_week[(team,w)][vol]+=max(0,num(r.get(vol)))
                    if opp:
                        for market in MARKETS:
                            allowed[(opp,w)][market]+=max(0,num(r.get(market)))
                            pos=str(r.get("position") or "").upper()
                            if pos:pos_allowed[(opp,w,pos)][market]+=max(0,num(r.get(market)))
            league={}
            pos_league={}
            for market in MARKETS:
                v=[x[market] for x in allowed.values() if x[market]>0]
                league[market]=sum(v)/len(v) if v else 1
                for pos in ("QB","RB","WR","TE"):
                    vals=[x[market] for (opp,w,p),x in pos_allowed.items() if p==pos]
                    pos_league[(pos,market)]=sum(vals)/len(vals) if vals else 0
            for actual in weeks[week]:
                team=str(actual["team"]);pid=str(actual["player_id"])
                past=history.get((team,pid),[])
                if len(past)<3 or week-int(past[-1]["week"])>2:continue
                opp=str(actual.get("opponent_team") or "")
                pos=str(past[-1].get("position") or "").upper()
                for market,volume in MARKETS.items():
                    last=past[-5:]
                    avg=sum(num(r.get(market)) for r in last)/len(last)
                    if avg<(85 if market=="passing_yards" else 18):continue
                    base,_,expected,_=project_yards(past,market,volume)
                    team_keys=sorted((k for k in team_week if k[0]==team),key=lambda x:x[1])
                    series=[team_week[k][volume] for k in team_keys if team_week[k][volume]>0]
                    if not series:continue
                    target=.65*sum(series[-4:])/len(series[-4:])+.35*sum(series)/len(series)
                    eligible=[]
                    for (t,p),records in history.items():
                        if t!=team or len(records)<3 or week-int(records[-1]["week"])>2:continue
                        rec=records[-5:]
                        vols=[max(0,num(x.get(volume))) for x in rec]
                        v=.7*sum(vols[-3:])/len(vols[-3:])+.3*sum(vols)/len(vols)
                        if v>0:eligible.append((p,v))
                    total=sum(v for _,v in eligible)
                    player_vol=next((v for p,v in eligible if p==pid),0)
                    if total<=0 or player_vol<=0:continue
                    allocated=target*player_vol/total
                    opp_vals=[v[market] for (t,w),v in allowed.items() if t==opp and v[market]>0]
                    opp_mean=sum(opp_vals)/len(opp_vals) if opp_vals else league[market]
                    team_signal=max(-1,min(1,(opp_mean/max(1,league[market])-1)*len(opp_vals)/(len(opp_vals)+6)))
                    pos_vals=[v[market] for (t,w,p),v in pos_allowed.items() if t==opp and p==pos]
                    neutral=pos_league.get((pos,market),0)
                    pos_mean=sum(pos_vals)/len(pos_vals) if pos_vals else neutral
                    pos_signal=max(-1,min(1,(pos_mean/max(1,neutral)-1)*len(pos_vals)/(len(pos_vals)+6))) if neutral else 0
                    actual_y=max(0,num(actual.get(market)))
                    row={"season":season,"week":week,"market":market,"actual":actual_y,"predictions":{}}
                    for name,(workload,defense,position) in VARIANTS.items():
                        # Workload adjustment interpolates individual forecast toward
                        # team-consistent allocation, with ±30% role safety cap.
                        role=allocated/max(.1,expected)
                        role=max(.70,min(1.30,role))
                        multiplier=(1+workload*(role-1))*(1+defense*team_signal+position*pos_signal)
                        row["predictions"][name]=max(0,base*multiplier)
                    output.append(row)
        for r in weeks[week]:
            history[(str(r["team"]),str(r["player_id"]))].append(r)
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",type=int,default=2016)
    p.add_argument("--end",type=int,default=2026)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    errors=defaultdict(list)
    for season in range(a.start,a.end+1):
        for row in predictions(load_season(season),season):
            for name,pred in row["predictions"].items():
                errors[(row["market"],name,season)].append(abs(pred-row["actual"]))
    train=range(a.start,a.end-1)
    holdout=range(a.end-1,a.end+1)
    def score(m,n,seasons):
        vals=[v for s in seasons for v in errors[(m,n,s)]]
        return sum(vals)/len(vals) if vals else None
    report={"status":"research_only","production_changed":False,
            "caveat":"Live shared projection core with historical team/defense features; not full live production replay or frozen shadow evaluation.",
            "markets":{}}
    for market in MARKETS:
        ranking=sorted(VARIANTS,key=lambda n:score(market,n,train) or float("inf"))
        selected=ranking[0]
        base=score(market,"live_core",holdout)
        candidate=score(market,selected,holdout)
        report["markets"][market]={
            "training_selected":selected,
            "holdout_seasons":list(holdout),
            "holdout_baseline_mae":round(base,3) if base is not None else None,
            "holdout_candidate_mae":round(candidate,3) if candidate is not None else None,
            "holdout_improvement_pct":round(100*(base-candidate)/base,2) if base else None,
            "variants":{n:{"train_mae":round(score(market,n,train),3),"holdout_mae":round(score(market,n,holdout),3),
                "holdout_samples":sum(len(errors[(market,n,s)]) for s in holdout),
                "by_season":{str(s):{"n":len(errors[(market,n,s)]),"mae":round(sum(errors[(market,n,s)])/len(errors[(market,n,s)]),3)} for s in range(a.start,a.end+1) if errors[(market,n,s)]}} for n in VARIANTS},
            "approved_for_promotion":False}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({m:{k:v[k] for k in ("training_selected","holdout_baseline_mae","holdout_candidate_mae","holdout_improvement_pct")} for m,v in report["markets"].items()},indent=2))
if __name__=="__main__":main()
