"""Export trained, strictly prior-week *research candidates* for live ML cards.

The user-visible ML estimate is distinct from the live production projection.
Never mark advanced challenger active without paired frozen live promotion evidence.
"""
import json,math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from research.free_nfl_feature_lab import MARKET_SOURCE,lagged_values

FAMILY="free-nfl-advanced-ridge-v1"
GROUPS={"baseline_features":(),"ngs":("ngs",),"snap_counts":("snap",),
        "pfr_advanced":("pfr",),"combined":("ngs","snap","pfr"),
        "weekly_workload":("workload",),"opponent_efficiency":("matchup",),
        "workload_matchup":("workload","matchup"),
        "advanced_workload":("ngs","snap","pfr","workload"),
        "advanced_matchup":("ngs","snap","pfr","matchup"),
        "advanced_all":("ngs","snap","pfr","workload","matchup")}
LIMIT=0.25

def feature_vector(row,groups):
    return row["base"]+[v for group in groups for v in row[group]]

def previous_week(target):
    year,week=target
    return (year,week-1) if week>1 else (year-1,18)

def fit_selected(rows,report,target):
    """Exactly the same feature ordering as the feature ablation."""
    selected={}
    for market in MARKET_SOURCE:
        choice=report["player"].get(market,{})
        variant=choice.get("research_winner")
        if variant not in GROUPS or (choice.get("relative_improvement_pct") or 0)<=0:
            continue
        groups=GROUPS[variant]
        train=[r for r in rows if r["market"]==market and r["key"]<target]
        if len(train)<100:continue
        X=np.asarray([feature_vector(r,groups) for r in train],dtype=float)
        y=np.asarray([r["actual"] for r in train],dtype=float)
        if not (np.isfinite(X).all() and np.isfinite(y).all()):continue
        model=make_pipeline(StandardScaler(),Ridge(alpha=100))
        model.fit(X,y)
        scaler=model.named_steps["standardscaler"]
        ridge=model.named_steps["ridge"]
        coef=ridge.coef_/scaler.scale_
        intercept=float(ridge.intercept_-np.dot(coef,scaler.mean_))
        if not (math.isfinite(intercept) and np.isfinite(coef).all()):continue
        last=max(r["key"] for r in train)
        selected[market]={"variant":variant,"feature_groups":list(groups),
            "coefficients":[float(x) for x in coef],"intercept":intercept,
            "trained_season":last[0],"trained_week":last[1],
            "training_rows":len(train),"holdout_rows":choice.get("samples",0),
            "holdout_weeks":choice.get("weeks",0),"holdout_improvement_pct":choice.get("relative_improvement_pct"),
            "active":False}
    return selected

def features_for_player(series,pfr_ids,pid,market,target,opponent=None):
    if market not in MARKET_SOURCE:return None
    pfr=pfr_ids.get(str(pid))
    ngs=lagged_values(series,MARKET_SOURCE[market],pid,target,3)
    snap=lagged_values(series,"snap",pfr,target,1) if pfr else ([0.0],0.0)
    pfr_features=lagged_values(series,"pfr_"+{"passing_yards":"pass","rushing_yards":"rush","receiving_yards":"rec"}[market],pfr,target,3) if pfr else ([0.0]*3,0.0)
    workload=lagged_values(series,"workload_"+market,pid,target,3)
    matchup=lagged_values(series,"matchup_"+market,opponent,target,3)
    return {"ngs":ngs[0]+[ngs[1]],"snap":snap[0]+[snap[1]],"pfr":pfr_features[0]+[pfr_features[1]],
            "workload":workload[0]+[workload[1]],"matchup":matchup[0]+[matchup[1]],"opponent":opponent}

def build_source_features(series,pfr_ids,players,target,models):
    result={}
    for player in players:
        pid,market,opponent=player.get('player_id'),player.get('stat_key'),player.get('opponent')
        if not pid or market not in models or not opponent:continue
        feature=features_for_player(series,pfr_ids,pid,market,target,opponent)
        entry=result.setdefault(str(pid),{})
        # Same player/market in multiple matchups is ambiguous; exclude it.
        if market in entry and entry[market] != feature:
            entry[market]=None
        elif market not in entry:
            entry[market]=feature
    return result

def write_outputs(rows,series,pfr_ids,selection,season,week,player_ids,
                  runtime_path,features_path):
    target=(int(season),int(week))
    models=fit_selected(rows,selection,target)
    generated=datetime.now(timezone.utc).isoformat()
    runtime={"family":FAMILY,"generated_at_utc":generated,"target_season":season,
             "target_week":week,"research_only":True,"production_changed":False,
             "models":models,"promotion_policy":"shadow only; evaluate exact matched frozen live pairs before any production promotion"}
    snapshot={"family":FAMILY,"generated_at_utc":generated,"target_season":season,
              "target_week":week,"research_only":True,
              "players":build_source_features(series,pfr_ids,player_ids,target,models)}
    runtime_path.write_text(json.dumps(runtime,indent=2)+"\n")
    features_path.write_text(json.dumps(snapshot,indent=2)+"\n")
    return runtime,snapshot
