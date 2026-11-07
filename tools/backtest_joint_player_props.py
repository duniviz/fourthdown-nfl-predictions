"""Research-only joint QB/receiver over-probability test.

Uses forecast means as proxy thresholds, NOT historical sportsbook lines.
A correlation model changes JOINT probabilities, not individual player
marginal probabilities. Fit correlation on 2016-24 only; test 2025-26.
"""
import argparse,json,math
from collections import defaultdict
from pathlib import Path
import numpy as np
import nflreadpy as nfl
from live.player_research import num,project_yards

def rows_for_season(season):
    weeks=defaultdict(list)
    for r in nfl.load_player_stats([season],summary_level="week").to_dicts():
        if str(r.get("season_type","REG")).upper() not in ("REG","2"):continue
        try:week=int(r["week"])
        except (ValueError,TypeError,KeyError):continue
        if 1<=week<=18 and r.get("team") and r.get("player_id"):weeks[week].append(r)
    history=defaultdict(list);pairs=[]
    for week,players in sorted(weeks.items()):
        eligible=defaultdict(list)
        for r in players:
            team=str(r["team"]);pid=str(r["player_id"]);pos=str(r.get("position") or "").upper()
            prior=history[(team,pid)]
            if len(prior)<3 or week-int(prior[-1]["week"])>2:continue
            if pos=="QB":
                market,vol="passing_yards","attempts"
                if sum(num(x.get(vol)) for x in prior[-5:])/len(prior[-5:])<15:continue
            elif pos in ("WR","TE","RB"):
                market,vol="receiving_yards","targets"
                if sum(num(x.get(market)) for x in prior[-5:])/len(prior[-5:])<18:continue
            else:continue
            pred,spread,_,_=project_yards(prior,market,vol)
            eligible[team].append({"id":pid,"position":pos,"market":market,
                                   "pred":pred,"spread":max(5,spread),
                                   "actual":num(r.get(market)),
                                   "prior_attempts":sum(num(x.get("attempts")) for x in prior[-3:])/min(3,len(prior))})
        for team,group in eligible.items():
            qbs=[x for x in group if x["position"]=="QB"]
            if not qbs:continue
            qb=max(qbs,key=lambda x:x["prior_attempts"]) # pregame-only QB choice
            for rec in group:
                if rec["market"]!="receiving_yards":continue
                pairs.append({"season":season,"week":week,"team":team,"position":rec["position"],
                              "x":(qb["actual"]-qb["pred"])/qb["spread"],
                              "y":(rec["actual"]-rec["pred"])/rec["spread"],
                              "qb_over":int(qb["actual"]>qb["pred"]),
                              "receiver_over":int(rec["actual"]>rec["pred"])})
        for r in players:history[(str(r["team"]),str(r["player_id"]))].append(r)
    return pairs

def metrics(rows,rho):
    if not rows:return {"pairs":0}
    # Empirical marginal over-rates from training are supplied separately.
    return {"pairs":len(rows),"rho":round(rho,4)}
def score(rows,probs):
    obs=np.array([r["qb_over"]*r["receiver_over"] for r in rows],dtype=float)
    p=np.asarray(probs)
    return {"pairs":len(rows),"observed_both_over_rate":round(float(obs.mean()),4),
            "predicted_both_over_rate":round(float(p.mean()),4),
            "brier":round(float(np.mean((p-obs)**2)),6)}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",type=int,default=2016)
    p.add_argument("--end",type=int,default=2026)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    data=[]
    for season in range(a.start,a.end+1):data.extend(rows_for_season(season))
    train=[r for r in data if r["season"]<=a.end-2]
    hold=[r for r in data if r["season"]>=a.end-1]
    if len(train)<100 or len(hold)<20:raise ValueError("Not enough training or holdout samples")
    # Each position group receives a training-only covariance and marginal rate.
    rng=np.random.default_rng(42)
    result={}
    for position in ("WR","TE","RB"):
        tr=[r for r in train if r["position"]==position]
        te=[r for r in hold if r["position"]==position]
        if len(tr)<100 or len(te)<20:continue
        rho=float(np.corrcoef([[r["x"] for r in tr],[r["y"] for r in tr]])[0,1])
        rho=float(np.clip(rho,-.8,.8))
        qrate=float(np.mean([r["qb_over"] for r in tr]))
        rrate=float(np.mean([r["receiver_over"] for r in tr]))
        # Gaussian copula using empirical marginal probabilities.
        # P(both over)=P(Z1>Phi^-1(1-qrate), Z2>Phi^-1(1-rrate)).
        from statistics import NormalDist
        normal=NormalDist()
        qcut=normal.inv_cdf(min(.999,max(.001,1-qrate)))
        rcut=normal.inv_cdf(min(.999,max(.001,1-rrate)))
        z=rng.standard_normal((300000,2))
        joint=float(np.mean((z[:,0]>qcut)&(rho*z[:,0]+math.sqrt(1-rho*rho)*z[:,1]>rcut)))
        independent=qrate*rrate
        result[position]={"train_pairs":len(tr),"holdout_pairs":len(te),
                          "train_residual_rho":round(rho,4),
                          "train_qb_over_rate":round(qrate,4),"train_receiver_over_rate":round(rrate,4),
                          "independent":score(te,[independent]*len(te)),
                          "correlated":score(te,[joint]*len(te)),
                          "improved_holdout_brier":score(te,[joint]*len(te))["brier"]<score(te,[independent]*len(te))["brier"]}
    report={"research_only":True,"production_changed":False,"approved_for_promotion":False,
            "train_seasons":[a.start,a.end-2],"holdout_seasons":[a.end-1,a.end],
            "test":"Joint probability that QB passing and same-team receiver receiving yards BOTH exceed their respective historical forecast means",
            "positions":result,
            "limitations":["Proxy thresholds are forecast means, not real sportsbook lines",
                           "Same QB may be paired with several receivers; pairs are not independent",
                           "Marginal rates and correlation estimated on training seasons only",
                           "Does not test individual over probabilities or prove individual projection improvement",
                           "Not production-equivalent and not eligible for promotion"]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
