#!/usr/bin/env python3
"""Research-only NFL game ML feature ablation with strict prior-week inputs.

Uses nflverse play-by-play and schedules. Every game in a week sees only
earlier weeks; no same-week result, future injuries, or future weather.
Unavailable pregame QB/injury/weather history is explicitly excluded.
"""
import json,math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor,HistGradientBoostingRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import nflreadpy as nfl

ROOT=Path(__file__).resolve().parents[1]
BASE=("week","home_points_for","home_points_against","away_points_for","away_points_against")
EXTRA=("home_epa","away_epa","home_success","away_success",
       "home_plays_per_game","away_plays_per_game","home_pass_rate","away_pass_rate",
       "home_pass_epa","away_pass_epa","home_rush_epa","away_rush_epa",
       "home_defense_epa_allowed","away_defense_epa_allowed",
       "home_redzone_rate","away_redzone_rate",
       "home_qb_proxy_epa","away_qb_proxy_epa")
def num(v):
 try:
  f=float(v)
  return f if math.isfinite(f) else None
 except (ValueError,TypeError):return None
def features(schedules,pbp):
 # Aggregate by season, week and team; never mix different seasons.
 weekly=defaultdict(lambda:defaultdict(list))
 for p in pbp:
  try:season=int(p["season"]);week=int(p["week"])
  except (KeyError,ValueError,TypeError):continue
  if p.get("season_type") not in ("REG",None) or p.get("play_type") not in ("pass","run"):continue
  offense=p.get("posteam");defense=p.get("defteam")
  if not offense or not defense:continue
  epa=num(p.get("epa"));success=num(p.get("success"));yardline=num(p.get("yardline_100"))
  for team,side in ((offense,"off"),(defense,"def")):
   a=weekly[(season,week,team)]
   a[side+"_plays"].append(1.)
   if epa is not None:a[side+"_epa"].append(epa)
  a=weekly[(season,week,offense)]
  if success is not None:a["success"].append(success)
  if p["play_type"]=="pass":
   a["pass"].append(1.)
   if epa is not None:a["pass_epa"].append(epa)
   # QB pass/dropback efficiency proxy; excludes unverified starter identity.
   if epa is not None:a["qb_proxy"].append(epa)
  elif epa is not None:a["rush_epa"].append(epa)
  if yardline is not None and yardline<=20:a["redzone"].append(1.)
 history=defaultdict(list);samples=[];last=None;pending=[]
 def flush():
  for key,item in pending:history[key].append(item)
  pending.clear()
 for g in sorted(schedules,key=lambda g:(int(g.get("season") or 0),int(g.get("week") or 0))):
  try:season=int(g["season"]);week=int(g["week"])
  except (KeyError,ValueError,TypeError):continue
  if g.get("game_type")!="REG":continue
  if last is not None and last!=(season,week):flush()
  last=(season,week)
  home=g.get("home_team");away=g.get("away_team")
  hs=num(g.get("home_score"));aws=num(g.get("away_score"))
  if not home or not away or hs is None or aws is None:continue
  def team(t):
   past=history[(season,t)][-5:]
   if len(past)<3:return None
   def avg(k,default=0):
    vals=[x[k] for x in past if x.get(k) is not None]
    return sum(vals)/len(vals) if vals else default
   return [avg("for"),avg("against"),avg("epa"),avg("success"),
           avg("plays"),avg("pass_rate"),avg("pass_epa"),avg("rush_epa"),
           avg("def_epa"),avg("redzone"),avg("qb_proxy")]
  h=team(home);a=team(away)
  if h and a:
   base=[week,h[0],h[1],a[0],a[1]]
   extended=base+[h[i] for i in range(2,11)]+[a[i] for i in range(2,11)]
   samples.append({"season":season,"week":week,"base":base,"extended":extended,
                   "game_id":str(g.get("game_id") or ""), "total":hs+aws,"margin":hs-aws})
  for team_name,pf,pa in ((home,hs,aws),(away,aws,hs)):
   w=weekly[(season,week,team_name)]
   def mean(k):
    v=w.get(k,[])
    return sum(v)/len(v) if v else None
   plays=len(w.get("off_plays",[]))
   pending.append(((season,team_name),{"for":pf,"against":pa,"epa":mean("off_epa"),
    "success":mean("success"),"plays":plays or None,
    "pass_rate":len(w.get("pass",[]))/plays if plays else None,
    "pass_epa":mean("pass_epa"),"rush_epa":mean("rush_epa"),
    "def_epa":mean("def_epa"),
    "redzone":len(w.get("redzone",[]))/plays if plays else None,
    "qb_proxy":mean("qb_proxy")}))
 flush()
 return samples
def evaluate(rows):
 # Walk-forward full-season holdouts. Historical baseline and expanded models
 # train on the same prior seasons and score the exact same held-out games.
 seasons=sorted({r["season"] for r in rows})
 out=[]
 for season in seasons:
  train=[r for r in rows if r["season"]<season]
  test=[r for r in rows if r["season"]==season]
  if len(train)<150 or len(test)<100:continue
  for market in ("total","margin"):
   y=np.array([r[market] for r in train]);actual=np.array([r[market] for r in test])
   for feature_set in ("base","extended"):
    x=np.array([r[feature_set] for r in train]);xt=np.array([r[feature_set] for r in test])
    models={"ridge":make_pipeline(StandardScaler(),Ridge(alpha=100)),
     "random_forest":RandomForestRegressor(n_estimators=100,max_depth=5,min_samples_leaf=12,random_state=42,n_jobs=1),
     "gradient_boosting":HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=9,min_samples_leaf=20,l2_regularization=20,random_state=42)}
    for name,model in models.items():
     pred=model.fit(x,y).predict(xt)
     out.append({"holdout_season":season,"market":market,"features":feature_set,"model":name,
                 "matched_games":len(test),"mae":round(float(np.mean(abs(pred-actual))),4),
                 "rmse":round(float(np.sqrt(np.mean((pred-actual)**2))),4)})
 return {"status":"RESEARCH_ONLY_FEATURE_ABLATION","production_modified":False,
         "not_live_comparison":True,"features_base":BASE,"features_extended":EXTRA,
         "exclusions":["Weather: no verified timestamped historical pregame weather",
          "Injuries and named starting QB: no verified timestamped historical pregame statuses",
          "Pressure rate: no independently verified historical pressure feed"],
         "results":out}
def main():
 seasons=list(range(2020,datetime.now(timezone.utc).year+1))
 schedules=nfl.load_schedules(seasons).to_dicts()
 pbp=[]
 for season in seasons:
  try:pbp.extend(nfl.load_pbp([season]).to_dicts())
  except Exception as exc:print("PBP unavailable",season,str(exc))
 if not pbp:raise RuntimeError("No verified PBP; no empty success report")
 report=evaluate(features(schedules,pbp))
 out=ROOT/"research/feature-ablation-results";out.mkdir(parents=True,exist_ok=True)
 (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
 print("Holdout evaluations:",len(report["results"]))
if __name__=="__main__":main()
