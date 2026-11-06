#!/usr/bin/env python3
"""Research-only QB injury designation x historical QB performance experiment.

Weekly reports are not verified timestamped pregame snapshots. This model is
NOT eligible for deployment; it tests whether an injury-specific interaction
is worth pursuing with validated availability and replacement starter data.
"""
import argparse,csv,json
from pathlib import Path
from collections import defaultdict
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from player_impact_research import load,feature,metric
from qb_efficiency_challenger import read_qb_stats,qb_features
from audit_historical_injuries import normalized_team

def qb_injury_reports(paths):
 status=defaultdict(set);coverage=set()
 for path in paths:
  with path.open(newline="",encoding="utf-8-sig") as f:
   rd=csv.DictReader(f)
   if not {"season","week","team","position"}.issubset(rd.fieldnames or []):raise ValueError("Missing injury fields")
   if not {"report_status","game_status"}.intersection(rd.fieldnames or []):raise ValueError("Missing status")
   for row in rd:
    try:y=int(row["season"]);w=int(row["week"])
    except (TypeError,ValueError):continue
    if y not in tuple(range(2020,2026)) or not 1<=w<=18:continue
    if row.get("game_type") and row["game_type"]!="REG":continue
    team=normalized_team(row["team"])
    coverage.add((y,w,team))
    if str(row.get("position") or "").upper().strip()!="QB":continue
    designation=str(row.get("report_status") or row.get("game_status") or "").lower().strip()
    if designation in ("out","doubtful"):
     identity=row.get("gsis_id") or row.get("player_id") or row.get("full_name") or row.get("player_name") or str(len(status[(y,w,team)]))
     status[(y,w,team)].add(str(identity))
 return status,coverage

def sample_games(games,qbs,injury,coverage):
 history=defaultdict(list);pending=[];bucket=None;out=[]
 for g in games:
  key=(g["season"],g["week"])
  if bucket is not None and key!=bucket:
   for k,v in pending:history[k].append(v)
   pending=[]
  bucket=key
  y,w=key;home=normalized_team(g["home_team"]);away=normalized_team(g["away_team"])
  base=feature(history,y,w,home,away)
  if base is not None and (y,w,home) in coverage and (y,w,away) in coverage:
   h=qb_features(qbs,y,w,home);a=qb_features(qbs,y,w,away)
   hi=min(len(injury[(y,w,home)]),2);ai=min(len(injury[(y,w,away)]),2)
   # Distinct QB injury flags + interaction with prior-only passing EPA.
   extra=[float(hi>0),float(ai>0),float(hi>0)*h[0],float(ai>0)*a[0]]
   out.append((y,base,extra,g["home_score"],g["away_score"],bool(hi or ai)))
  pending.extend([((y,home),(w,g["home_score"],g["away_score"])),((y,away),(w,g["away_score"],g["home_score"]))])
 return out

def evaluate(rows):
 report={"status":"RESEARCH_ONLY_QB_INJURY_INTERACTION","production_modified":False,"promotion_eligible":False,
  "verified_injured_starting_qbs":0,"verified_replacement_starters":0,"paired_games":len(rows),
  "method":"Out/Doubtful QB weekly report designation and interaction with prior-five-week team QB EPA; chronological Ridge versus matched baseline",
  "limitation":"Injury report rows lack verified publication timestamps and do not prove designated QB was the starter or replacement; no deployment or causal point adjustment.",
  "seasons":{}}
 for year in (2024,2025):
  tr=[r for r in rows if r[0]<year];te=[r for r in rows if r[0]==year]
  res={"train_n":len(tr),"test_n":len(te),"qb_flag_games":sum(r[5] for r in te),"metrics":{},"qb_flag_subset":{}}
  if len(tr)<100 or len(te)<30:
   res["status"]="INSUFFICIENT_DATA";report["seasons"][str(year)]=res;continue
  pred={}
  for label,enhanced in (("baseline",False),("qb_injury_interaction",True)):
   x=np.array([r[1]+(r[2] if enhanced else []) for r in tr])
   xt=np.array([r[1]+(r[2] if enhanced else []) for r in te])
   ph=make_pipeline(StandardScaler(),Ridge(alpha=100)).fit(x,[r[3] for r in tr]).predict(xt)
   pa=make_pipeline(StandardScaler(),Ridge(alpha=100)).fit(x,[r[4] for r in tr]).predict(xt)
   pred[label]=(ph,pa)
  h=np.array([r[3] for r in te]);a=np.array([r[4] for r in te]);subset=[i for i,r in enumerate(te) if r[5]]
  for name,actual in (("home_score",h),("away_score",a),("margin_home",h-a),("total",h+a)):
   res["metrics"][name]={}
   for label,(ph,pa) in pred.items():
    yhat={"home_score":ph,"away_score":pa,"margin_home":ph-pa,"total":ph+pa}[name]
    res["metrics"][name][label]=metric(actual,yhat)
    if subset:res["qb_flag_subset"].setdefault(name,{})[label]=metric(actual[subset],yhat[subset])
   res["metrics"][name]["mae_change"]=round(res["metrics"][name]["qb_injury_interaction"]["mae"]-res["metrics"][name]["baseline"]["mae"],4)
  res["status"]="HISTORICAL_PROXY_ONLY";report["seasons"][str(year)]=res
 return report

def main():
 p=argparse.ArgumentParser();p.add_argument("--schedule",required=True,type=Path);p.add_argument("--qb-stats",required=True,type=Path,nargs="+");p.add_argument("--injuries",required=True,type=Path,nargs="+");p.add_argument("--output",required=True,type=Path)
 a=p.parse_args();inj,coverage=qb_injury_reports(a.injuries)
 report=evaluate(sample_games(load(a.schedule),read_qb_stats(a.qb_stats),inj,coverage))
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2))
if __name__=="__main__":main()
