#!/usr/bin/env python3
"""Research-only chronological QB efficiency challenger.

QB selection uses ONLY earlier weekly stats. Selection is a heuristic, not
a verified announced starter. No postgame participation from target game.
"""
import argparse,csv,json
from collections import defaultdict
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from player_impact_research import load,feature,metric
from audit_historical_injuries import normalized_team

def read_qb_stats(paths):
 rows=defaultdict(list)
 for path in paths:
  with path.open(newline="",encoding="utf-8-sig") as f:
   rd=csv.DictReader(f)
   cols=set(rd.fieldnames or [])
   if not {"season","week","team","passing_epa","attempts"}.issubset(cols):
    raise ValueError("Missing required weekly QB columns: "+str(sorted({"season","week","team","passing_epa","attempts"}-cols)))
   player_key="player_id" if "player_id" in cols else "player_name" if "player_name" in cols else None
   if not player_key:raise ValueError("No stable player identity column")
   for r in rd:
    try:
     y=int(r["season"]);w=int(r["week"]);attempts=float(r["attempts"] or 0);epa=float(r["passing_epa"] or 0)
    except (TypeError,ValueError):continue
    if y not in tuple(range(2016,2026)) or not 1<=w<=18 or attempts<1:continue
    if r.get("season_type") and r["season_type"] not in ("REG","REGULAR"):continue
    rows[(y,w,normalized_team(r["team"]))].append((r[player_key],attempts,epa))
 return rows

def qb_features(rows,year,week,team):
 """Prior 5 games only, shrink QB EPA/attempt to league neutral."""
 prior=defaultdict(lambda:[0.,0.,0])
 for w in range(max(1,week-5),week):
  for player,attempts,epa in rows.get((year,w,team),[]):
   v=prior[player];v[0]+=attempts;v[1]+=epa;v[2]+=1
 if not prior:return [0.,0.,0.]
 starter=max(prior.items(),key=lambda x:(x[1][0],x[0]))[0]
 a,e,g=prior[starter]
 # No claim that this QB will start. Empirical-Bayes shrinkage, 100 attempts.
 return [e/(a+100),min(a,200)/200.,min(g,5)/5.]

def make_samples(games,rows):
 history=defaultdict(list);pending=[];bucket=None;samples=[]
 for g in games:
  key=(g["season"],g["week"])
  if bucket is not None and key!=bucket:
   for k,v in pending:history[k].append(v)
   pending=[]
  bucket=key
  year,week=key;home=normalized_team(g["home_team"]);away=normalized_team(g["away_team"])
  base=feature(history,year,week,home,away)
  if base is not None:
   qb=qb_features(rows,year,week,home)+qb_features(rows,year,week,away)
   samples.append((year,base,qb,g["home_score"],g["away_score"]))
  pending.extend([((year,home),(week,g["home_score"],g["away_score"])),((year,away),(week,g["away_score"],g["home_score"]))])
 return samples

def evaluate(samples):
 report={"status":"RESEARCH_ONLY_QB_EFFICIENCY_PROXY","production_modified":False,
         "verified_starter_changes":0,"promotion_eligible":False,
         "limitation":"Highest prior-five-week passing attempts is NOT a confirmed upcoming starter; this is historical QB efficiency research, not an injury point adjustment.",
         "seasons":{},"eligible_games":len(samples)}
 for season in (2024,2025):
  train=[r for r in samples if r[0]<season];test=[r for r in samples if r[0]==season]
  result={"train_n":len(train),"test_n":len(test),"metrics":{}}
  if len(train)<100 or len(test)<30:
   result["status"]="INSUFFICIENT_DATA";report["seasons"][str(season)]=result;continue
  preds={}
  for label,add in (("baseline",False),("qb_efficiency",True)):
   tx=np.array([r[1]+(r[2] if add else []) for r in train])
   vx=np.array([r[1]+(r[2] if add else []) for r in test])
   ph=make_pipeline(StandardScaler(),Ridge(alpha=100)).fit(tx,[r[3] for r in train]).predict(vx)
   pa=make_pipeline(StandardScaler(),Ridge(alpha=100)).fit(tx,[r[4] for r in train]).predict(vx)
   preds[label]=(ph,pa)
  h=np.array([r[3] for r in test]);a=np.array([r[4] for r in test])
  for name,truth in (("home_score",h),("away_score",a),("margin_home",h-a),("total",h+a)):
   result["metrics"][name]={}
   for label,(ph,pa) in preds.items():
    predicted={"home_score":ph,"away_score":pa,"margin_home":ph-pa,"total":ph+pa}[name]
    result["metrics"][name][label]=metric(truth,predicted)
   result["metrics"][name]["mae_change"]=round(result["metrics"][name]["qb_efficiency"]["mae"]-result["metrics"][name]["baseline"]["mae"],4)
  result["status"]="HISTORICAL_HOLDOUT_COMPLETE";report["seasons"][str(season)]=result
 return report

def main():
 p=argparse.ArgumentParser();p.add_argument("--schedule",required=True,type=Path);p.add_argument("--qb-stats",required=True,type=Path,nargs="+");p.add_argument("--output",required=True,type=Path);a=p.parse_args()
 report=evaluate(make_samples(load(a.schedule),read_qb_stats(a.qb_stats)))
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2))
if __name__=="__main__":main()
