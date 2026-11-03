#!/usr/bin/env python3
"""Leakage-safe historical NFL game challengers. Research only, no live model edits."""
import json,math
from collections import defaultdict,deque
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import polars as pl
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor,HistGradientBoostingRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data/training"
def rows_from_schedules(df):
 required={"season","week","home_team","away_team","home_score","away_score"}
 if not required.issubset(df.columns):raise ValueError("Schedule schema missing "+str(required-set(df.columns)))
 rows=df.to_dicts()
 rows.sort(key=lambda r:(int(r["season"] or 0),int(r["week"] or 0),str(r.get("gameday") or ""),str(r.get("gametime") or "")))
 # Features must only use games from earlier weeks, never another game in current week.
 history=defaultdict(lambda:deque(maxlen=6))
 output=[]
 current_week=None;pending=[]
 def flush():
  for team,pts,allowed in pending:history[team].append((pts,allowed))
  pending.clear()
 for r in rows:
  season,week=r["season"],r["week"]
  if season is None or week is None:continue
  season,week=int(season),int(week)
  key=(season,week)
  if current_week is not None and key!=current_week:flush()
  current_week=key
  if str(r.get("game_type") or "REG") not in ("REG","WC","DIV","CON","SB"):continue
  h,a=r["home_team"],r["away_team"]
  if not h or not a or h==a:continue
  try:
   hs,aws=float(r["home_score"]),float(r["away_score"])
  except (TypeError,ValueError):continue
  if not all(math.isfinite(v) and v>=0 for v in (hs,aws)):continue
  hh=list(history[(season,h)]);ah=list(history[(season,a)])
  def avg(xs,idx,default):return sum(v[idx] for v in xs)/len(xs) if xs else default
  # Only past scores and allowances, season/week, home field and sample counts.
  features=[week,min(len(hh),6),min(len(ah),6),
            avg(hh,0,22),avg(hh,1,22),avg(ah,0,22),avg(ah,1,22),
            avg(hh,0,22)-avg(ah,1,22),avg(ah,0,22)-avg(hh,1,22)]
  output.append({"season":season,"week":week,"features":features,
                 "total":hs+aws,"margin":hs-aws,"winner":int(hs>aws)})
  pending.extend([( (season,h),hs,aws),((season,a),aws,hs)])
 flush()
 return output

def evaluate(rows):
 seasons=sorted({r["season"] for r in rows})
 if len(seasons)<3:raise ValueError("At least three seasons required for train, validation, holdout")
 holdout=seasons[-1]
 # Holdout latest full season if current season has fewer than 150 completed games.
 if sum(r["season"]==holdout for r in rows)<150:holdout=seasons[-2]
 train=[r for r in rows if r["season"]<holdout]
 test=[r for r in rows if r["season"]==holdout]
 if len(train)<150 or len(test)<150:raise ValueError("Insufficient chronological train or holdout games")
 x=np.asarray([r["features"] for r in train],float)
 xt=np.asarray([r["features"] for r in test],float)
 result={"train_seasons":sorted({r["season"] for r in train}),"holdout_season":holdout,
         "train_games":len(train),"holdout_games":len(test),"markets":{}}
 models={
  "ridge":lambda:make_pipeline(StandardScaler(),Ridge(alpha=100)),
  "random_forest":lambda:RandomForestRegressor(n_estimators=100,max_depth=5,min_samples_leaf=12,random_state=42,n_jobs=1),
  "gradient_boosting":lambda:HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=9,min_samples_leaf=20,l2_regularization=20,random_state=42)}
 for target in ("total","margin"):
  y=np.asarray([r[target] for r in train],float)
  yt=np.asarray([r[target] for r in test],float)
  baseline=np.full(len(test),np.mean(y))
  score={"simple_training_mean_mae":round(float(np.mean(abs(yt-baseline))),3),"challengers":{}}
  for name,make in models.items():
   model=make();model.fit(x,y);pred=model.predict(xt)
   score["challengers"][name]={"mae":round(float(np.mean(abs(yt-pred))),3),
    "rmse":round(float(np.sqrt(np.mean((yt-pred)**2))),3)}
   if target=="margin":
    valid=yt!=0
    score["challengers"][name]["winner_accuracy_excluding_ties"]=round(float(np.mean((pred[valid]>0)==(yt[valid]>0))),4)
  result["markets"][target]=score
 result.update({"generated_at_utc":datetime.now(timezone.utc).isoformat(),
  "research_only":True,"production_changed":False,"automatic_promotion":False,
  "feature_policy":"Prior completed weeks only; season-local rolling scores and allowances; no same-week outcomes",
  "limitations":"Not benchmarked against frozen FOURTHDOWN projections or timestamped DK lines; training-mean baseline only. No ATS or O/U market grading."})
 return result
def main():
 report=evaluate(rows_from_schedules(pl.read_parquet(DATA/"schedules.parquet")))
 (DATA/"game-ml-review.json").write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps(report,indent=2))
if __name__=="__main__":main()
