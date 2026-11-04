#!/usr/bin/env python3
"""Exploratory injury-designation proxy, NOT verified player WAR/PAR.

Weekly nflverse designations lack row-level capture timestamps and starter IDs.
Do not interpret an Out/Doubtful count as a confirmed absence or deploy this.
"""
import argparse,csv,json
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from player_impact_research import load,feature,metric
from audit_historical_injuries import GROUPS,normalized_team
GROUP_ORDER=("QB","WR","RB","OL","Defense")
def read_injuries(paths):
 counts=Counter();covered=set()
 for path in paths:
  with path.open(newline="",encoding="utf-8-sig") as f:
   reader=csv.DictReader(f)
   if not {"season","week","team","position"}.issubset(reader.fieldnames or []):raise ValueError("Missing injury columns")
   if not {"report_status","game_status"}.intersection(reader.fieldnames or []):raise ValueError("Missing designation column")
   for r in reader:
    try:season=int(r["season"]);week=int(r["week"])
    except (ValueError,TypeError):continue
    if season not in (2023,2024,2025) or not 1<=week<=18 or (r.get("game_type") and r["game_type"]!="REG"):continue
    team=normalized_team(r["team"]);group=GROUPS.get(str(r["position"]).strip().upper())
    if not group:continue
    covered.add((season,week,team))
    status=str(r.get("report_status") or r.get("game_status") or "").lower().strip()
    if status in ("out","doubtful"):counts[(season,week,team,group)]+=1
 return counts,covered
def samples(games,counts,covered):
 history=defaultdict(list);pending=[];bucket=None;rows=[]
 for g in games:
  key=(g["season"],g["week"])
  if bucket is not None and key!=bucket:
   for k,v in pending:history[k].append(v)
   pending=[]
  bucket=key
  season,week=key;home=normalized_team(g["home_team"]);away=normalized_team(g["away_team"])
  x=feature(history,season,week,home,away)
  if x is not None and (season,week,home) in covered and (season,week,away) in covered:
   injury=[counts[(season,week,team,group)] for team in (home,away) for group in GROUP_ORDER]
   rows.append((season,x,injury,g["home_score"],g["away_score"],sum(injury)>0))
  pending.extend([((season,home),(week,g["home_score"],g["away_score"])),((season,away),(week,g["away_score"],g["home_score"]))])
 return rows
def evaluate(rows):
 report={"status":"EXPLORATORY_INJURY_DESIGNATION_PROXY_ONLY","production_modified":False,
  "data_quality":"weekly designations without verifiable publication timestamps; replacement starters not identified",
  "positions":list(GROUP_ORDER),"eligible_paired_games":len(rows),"seasons":{},
  "not_player_war":True,"promotion_eligible":False}
 for season in (2024,2025):
  train=[r for r in rows if r[0]<season];test=[r for r in rows if r[0]==season]
  out={"train_n":len(train),"test_n":len(test),"injury_designation_games":sum(r[5] for r in test),"metrics":{}}
  if len(train)<100 or len(test)<30:
   out["status"]="INSUFFICIENT_PAIRED_DATA";report["seasons"][str(season)]=out;continue
  x=np.array([r[1] for r in train]);xt=np.array([r[1] for r in test])
  xi=np.array([r[1]+r[2] for r in train]);xit=np.array([r[1]+r[2] for r in test])
  actualh=np.array([r[3] for r in test]);actuala=np.array([r[4] for r in test])
  predictions={}
  for label,trainx,testx in (("baseline",x,xt),("injury_designation_proxy",xi,xit)):
   ph=make_pipeline(StandardScaler(),Ridge(alpha=100)).fit(trainx,[r[3] for r in train]).predict(testx)
   pa=make_pipeline(StandardScaler(),Ridge(alpha=100)).fit(trainx,[r[4] for r in train]).predict(testx)
   predictions[label]=(ph,pa)
  for name,truth in (("home_score",actualh),("away_score",actuala),("margin_home",actualh-actuala),("total",actualh+actuala)):
   out["metrics"][name]={}
   for label,(ph,pa) in predictions.items():
    pred={"home_score":ph,"away_score":pa,"margin_home":ph-pa,"total":ph+pa}[name]
    out["metrics"][name][label]=metric(truth,pred)
   out["metrics"][name]["mae_change_vs_baseline"]=round(out["metrics"][name]["injury_designation_proxy"]["mae"]-out["metrics"][name]["baseline"]["mae"],4)
  subset=[i for i,r in enumerate(test) if r[5]]
  out["injury_subset"]={"n":len(subset),"metrics":{}}
  for name,truth in (("margin_home",actualh-actuala),("total",actualh+actuala)):
   for label,(ph,pa) in predictions.items():
    pred={"margin_home":ph-pa,"total":ph+pa}[name]
    out["injury_subset"]["metrics"].setdefault(name,{})[label]=metric(truth[subset],pred[subset]) if subset else None
  out["status"]="HISTORICAL_PROXY_COMPARISON_ONLY";report["seasons"][str(season)]=out
 return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--schedule",required=True,type=Path);p.add_argument("--injuries",required=True,type=Path,nargs="+");p.add_argument("--output",required=True,type=Path);a=p.parse_args()
 counts,covered=read_injuries(a.injuries);result=evaluate(samples(load(a.schedule),counts,covered))
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result,indent=2))
if __name__=="__main__":main()
