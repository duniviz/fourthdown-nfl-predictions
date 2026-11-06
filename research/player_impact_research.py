#!/usr/bin/env python3
"""Research-only chronological player-availability impact experiment.

No final-box-score-derived injury features. No changes to production.
"""
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
POSITIONS=("QB","WR","RB","OL","Defense")
def number(x):
 try:
  v=float(x);return v if math.isfinite(v) else None
 except (ValueError,TypeError):return None
def load(path):
 with open(path,newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
 games=[]
 for r in rows:
  try:
   season=int(r["season"]);week=int(r["week"]);h=number(r.get("home_score"));a=number(r.get("away_score"))
   if season not in tuple(range(2016,2026)) or r.get("game_type","REG")!="REG" or not 1<=week<=18 or h is None or a is None:continue
   games.append(dict(r,season=season,week=week,home_score=h,away_score=a))
  except (ValueError,KeyError,TypeError):continue
 return sorted(games,key=lambda g:(g["season"],g["week"],g.get("gameday",""),g.get("game_id","")))
def feature(history,season,week,home,away):
 def team(t):
  rows=[r for r in history[(season,t)] if r[0]<week][-5:]
  if len(rows)<3:return None
  return [sum(r[j] for r in rows)/len(rows) for j in (1,2)]
 h=team(home);a=team(away)
 return h+a+[week] if h and a else None
def metric(actual,pred):
 a=np.asarray(actual);p=np.asarray(pred);e=a-p
 return {"n":len(a),"mae":round(float(np.abs(e).mean()),4),"rmse":round(float(np.sqrt(np.mean(e*e))),4)}
def evaluate(games):
 history=defaultdict(list);pending=[];current=None;samples=[]
 for g in games:
  bucket=(g["season"],g["week"])
  if current is not None and current!=bucket:
   for key,val in pending:history[key].append(val)
   pending=[]
  current=bucket
  home=g["home_team"];away=g["away_team"]
  x=feature(history,g["season"],g["week"],home,away)
  if x:samples.append((g["season"],x,g["home_score"],g["away_score"]))
  pending.extend([((g["season"],home),(g["week"],g["home_score"],g["away_score"])),((g["season"],away),(g["week"],g["away_score"],g["home_score"]))])
 report={"status":"RESEARCH_ONLY_INJURY_DATA_BLOCKED","production_modified":False,"positions":list(POSITIONS),
  "scope":"2016-2025 regular-season games","eligible_baseline_games":len(samples),
  "verified_pregame_injury_games":0,"seasons":{},
  "limitation":"No historical timestamped, complete pregame player availability and replacement-starter coverage was supplied. Do not fabricate player WAR/PAR or infer injury absences from postgame participation."}
 for season in (2024,2025):
  train=[r for r in samples if r[0]<season];test=[r for r in samples if r[0]==season]
  result={"train_n":len(train),"test_n":len(test),"baseline":{},"player_impact":None,
          "injury_specific":{"n":0,"mae":None,"rmse":None,"status":"NOT_EVALUABLE"}}
  if len(train)<100 or len(test)<30:result["status"]="INSUFFICIENT_BASELINE_GAMES"
  else:
   x=np.asarray([r[1] for r in train]);xt=np.asarray([r[1] for r in test])
   mh=make_pipeline(StandardScaler(),Ridge(alpha=100)).fit(x,[r[2] for r in train])
   ma=make_pipeline(StandardScaler(),Ridge(alpha=100)).fit(x,[r[3] for r in train])
   ph=mh.predict(xt);pa=ma.predict(xt)
   h=np.asarray([r[2] for r in test]);a=np.asarray([r[3] for r in test])
   for name,actual,pred in (("home_score",h,ph),("away_score",a,pa),("margin_home",h-a,ph-pa),("total",h+a,ph+pa)):
    result["baseline"][name]=metric(actual,pred)
   result["status"]="BASELINE_VERIFIED_INJURY_MODEL_NOT_EVALUABLE"
  report["seasons"][str(season)]=result
 return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--schedule",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
 a=p.parse_args();report=evaluate(load(a.schedule));a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2))
if __name__=="__main__":main()
