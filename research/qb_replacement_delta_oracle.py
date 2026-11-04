#!/usr/bin/env python3
"""Research-only retrospective QB replacement value test.

Uses target-game actual starter identity from completed-game schedule:
ORACLE / hindsight diagnostic, NOT pregame-valid and NEVER promotion eligible.
All efficiency statistics are computed from prior weeks only.
"""
import argparse,csv,json
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from player_impact_research import load,feature,metric
from audit_historical_injuries import normalized_team
from qb_efficiency_challenger import read_qb_stats

def qb_prior(qbs,year,week,team):
 players=defaultdict(lambda:[0.,0.])
 for w in range(max(1,week-8),week):
  for pid,att,epa in qbs.get((year,w,team),[]):
   players[pid][0]+=att;players[pid][1]+=epa
 return players

def samples(games,qbs):
 history=defaultdict(list);pending=[];bucket=None;out=[];counts=Counter()
 for g in games:
  key=(g["season"],g["week"])
  if bucket is not None and key!=bucket:
   for k,v in pending:history[k].append(v)
   pending=[]
  bucket=key
  y,w=key;home=normalized_team(g["home_team"]);away=normalized_team(g["away_team"])
  base=feature(history,y,w,home,away)
  if base is not None:
   extra=[];changed=False;complete=True
   for side,team in (("home",home),("away",away)):
    pid=str(g.get(side+"_qb_id") or "").strip()
    prior=qb_prior(qbs,y,w,team)
    if not pid or not prior:complete=False;break
    expected=max(prior,key=lambda p:prior[p][0])
    changed|=pid!=expected
    expected_a,expected_e=prior[expected]
    actual_a,actual_e=prior.get(pid,[0.,0.])
    # Empirical-Bayes neutral shrinkage for unobserved backups.
    delta=actual_e/(actual_a+100.)-expected_e/(expected_a+100.)
    extra.extend([delta,float(pid!=expected),min(actual_a,200)/200.])
   if complete:
    out.append((y,base,extra,g["home_score"],g["away_score"],changed))
    counts["retrospective_change_games"]+=int(changed)
  pending.extend([((y,home),(w,g["home_score"],g["away_score"])),((y,away),(w,g["away_score"],g["home_score"]))])
 return out,counts

def evaluate(rows,counts):
 result={"status":"HINDSIGHT_ORACLE_QB_REPLACEMENT_DIAGNOSTIC","production_modified":False,
 "promotion_eligible":False,"verified_pregame_starters":0,
 "critical_leakage_warning":"Target-game starter identities are postgame schedule fields; test uses hindsight and cannot estimate live predictive performance.",
 "sample_count":len(rows),"retrospective_change_games":counts["retrospective_change_games"],"seasons":{}}
 for year in (2024,2025):
  tr=[r for r in rows if r[0]<year];te=[r for r in rows if r[0]==year]
  d={"train_n":len(tr),"test_n":len(te),"changed_test_n":sum(r[5] for r in te),"all_games":{},"changed_games":{}}
  if len(tr)<100 or len(te)<30:
   d["status"]="INSUFFICIENT_DATA";result["seasons"][str(year)]=d;continue
  preds={}
  for label,add in (("baseline",False),("oracle_qb_delta",True)):
   x=np.asarray([r[1]+(r[2] if add else []) for r in tr])
   xt=np.asarray([r[1]+(r[2] if add else []) for r in te])
   ph=make_pipeline(StandardScaler(),Ridge(alpha=100)).fit(x,[r[3] for r in tr]).predict(xt)
   pa=make_pipeline(StandardScaler(),Ridge(alpha=100)).fit(x,[r[4] for r in tr]).predict(xt)
   preds[label]=(ph,pa)
  h=np.asarray([r[3] for r in te]);a=np.asarray([r[4] for r in te]);idx=[i for i,r in enumerate(te) if r[5]]
  for name,actual in (("spread",h-a),("total",h+a),("home",h),("away",a)):
   for label,(ph,pa) in preds.items():
    predicted={"spread":ph-pa,"total":ph+pa,"home":ph,"away":pa}[name]
    d["all_games"].setdefault(name,{})[label]=metric(actual,predicted)
    if idx:d["changed_games"].setdefault(name,{})[label]=metric(actual[idx],predicted[idx])
  d["status"]="ORACLE_DIAGNOSTIC_ONLY";result["seasons"][str(year)]=d
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument("--schedule",required=True,type=Path);p.add_argument("--qb-stats",required=True,type=Path,nargs="+");p.add_argument("--output",required=True,type=Path);a=p.parse_args()
 rows,counts=samples(load(a.schedule),read_qb_stats(a.qb_stats));report=evaluate(rows,counts)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2))
if __name__=="__main__":main()
