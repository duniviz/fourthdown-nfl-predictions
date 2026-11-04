#!/usr/bin/env python3
"""QB points-above-replacement research lab: chronological ML comparisons.

CRITICAL: target-game QB identities are retrospective schedule labels. These
experiments are hindsight diagnostics, not leakage-free pregame validation.
No model is saved for production or eligible for automatic promotion.
"""
import argparse,json
from pathlib import Path
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler,PolynomialFeatures
from sklearn.linear_model import Ridge,HuberRegressor
from sklearn.ensemble import RandomForestRegressor,HistGradientBoostingRegressor
from player_impact_research import load,metric
from qb_efficiency_challenger import read_qb_stats
from qb_replacement_delta_oracle import samples

def algorithms():
 return {
  "ridge":lambda:make_pipeline(StandardScaler(),Ridge(alpha=100)),
  "huber":lambda:make_pipeline(StandardScaler(),HuberRegressor(epsilon=1.5,max_iter=500)),
  "random_forest":lambda:RandomForestRegressor(n_estimators=180,max_depth=4,min_samples_leaf=15,random_state=42,n_jobs=1),
  "gradient_boosting":lambda:HistGradientBoostingRegressor(max_iter=90,max_leaf_nodes=7,min_samples_leaf=20,l2_regularization=10,learning_rate=.04,random_state=42),
  "polynomial_ridge":lambda:make_pipeline(StandardScaler(),PolynomialFeatures(degree=2,include_bias=False),Ridge(alpha=500))
 }

def run(rows):
 report={"status":"RESEARCH_ONLY_QB_PAR_MULTIMODEL_ORACLE",
 "promotion_eligible":False,"production_modified":False,"pregame_valid":False,
 "leakage_warning":"Actual target-game QB starter is taken from completed-game schedule. All candidate comparisons are hindsight diagnostics, NOT valid pregame prediction accuracy.",
 "formula":"Prior-eight-week QB passing EPA / (attempts + 100) replacement minus expected QB, with a starter-change flag and sample size; learned effect by multiple estimators.",
 "holdouts":{},"candidate_models":list(algorithms())}
 for season in (2024,2025):
  tr=[r for r in rows if r[0]<season];te=[r for r in rows if r[0]==season]
  d={"train_n":len(tr),"test_n":len(te),"changed_games_n":sum(r[5] for r in te),"models":{}}
  if len(tr)<100 or len(te)<30:
   d["status"]="INSUFFICIENT_DATA";report["holdouts"][str(season)]=d;continue
  h=np.array([r[3] for r in te]);a=np.array([r[4] for r in te])
  idx=np.array([i for i,r in enumerate(te) if r[5]],dtype=int)
  for label in ["baseline"]+list(algorithms()):
   add=label!="baseline"
   x=np.array([r[1]+(r[2] if add else []) for r in tr])
   xt=np.array([r[1]+(r[2] if add else []) for r in te])
   def model():
    return make_pipeline(StandardScaler(),Ridge(alpha=100)) if label=="baseline" else algorithms()[label]()
   try:
    ph=model().fit(x,[r[3] for r in tr]).predict(xt)
    pa=model().fit(x,[r[4] for r in tr]).predict(xt)
    if not (np.isfinite(ph).all() and np.isfinite(pa).all()):raise ValueError("Nonfinite predictions")
    d["models"][label]={"all":{"spread":metric(h-a,ph-pa),"total":metric(h+a,ph+pa)},
      "changed_games":{"spread":metric((h-a)[idx],(ph-pa)[idx]),"total":metric((h+a)[idx],(ph+pa)[idx])} if len(idx) else None}
   except (ValueError,FloatingPointError) as exc:d["models"][label]={"error":str(exc)}
  d["status"]="HINDSIGHT_ONLY_NO_PROMOTION";report["holdouts"][str(season)]=d
 return report

def main():
 p=argparse.ArgumentParser();p.add_argument("--schedule",required=True,type=Path);p.add_argument("--qb-stats",required=True,type=Path,nargs="+");p.add_argument("--output",required=True,type=Path)
 a=p.parse_args();rows,_=samples(load(a.schedule),read_qb_stats(a.qb_stats));result=run(rows)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n")
 print(json.dumps(result,indent=2))
if __name__=="__main__":main()
