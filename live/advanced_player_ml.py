"""Fail-closed inference for free NFL feature ML research cards.

Never overrides live production projections. Uses the exact feature ordering
from the walk-forward research trainer and source snapshots from before target week.
"""
import json,math
from pathlib import Path

FAMILY="free-nfl-advanced-ridge-v1"
MARKETS=("passing_yards","rushing_yards","receiving_yards")
GROUPS={"baseline_features":(),"ngs":("ngs",),"snap_counts":("snap",),
        "pfr_advanced":("pfr",),"combined":("ngs","snap","pfr")}
DIMENSIONS={"ngs":4,"snap":2,"pfr":4}

def load_pair(runtime_path=Path("data/player-advanced-ml-runtime.json"),
              features_path=Path("data/player-advanced-ml-features.json")):
    try:
        runtime=json.loads(runtime_path.read_text())
        features=json.loads(features_path.read_text())
        fields=("family","target_season","target_week","generated_at_utc")
        if any(runtime.get(k)!=features.get(k) for k in fields):return {},{}
        if runtime.get("family")!=FAMILY or not runtime.get("research_only") or not features.get("research_only"):
            return {},{}
        if not isinstance(runtime.get("models"),dict) or not isinstance(features.get("players"),dict):
            return {},{}
        return runtime,features
    except (OSError,ValueError,TypeError,AttributeError):return {},{}

def candidate(runtime,features,market,player_id,season,week,base,old,
              prior_games,recent_volume,recent_yards,team_volume,opponent_ratio):
    try:
        if market not in MARKETS or runtime.get("family")!=FAMILY or features.get("family")!=FAMILY:
            return None
        if (int(runtime["target_season"]),int(runtime["target_week"]))!=(int(season),int(week)):
            return None
        if (int(features["target_season"]),int(features["target_week"]))!=(int(season),int(week)):
            return None
        if runtime.get("generated_at_utc")!=features.get("generated_at_utc"):return None
        model=runtime["models"][market]
        trained=(int(model["trained_season"]),int(model["trained_week"]))
        target=(int(season),int(week))
        if trained>=target:return None
        # Never use a stale model just because the feature file was regenerated.
        if not ((trained[0]==target[0] and target[1]-trained[1]<=2) or
                (trained[0]+1==target[0] and trained[1]>=17 and target[1]<=2)):return None
        variant=model["variant"]
        groups=GROUPS[variant]
        if model.get("feature_groups")!=list(groups) or model.get("active") is not False:return None
        inputs=features["players"][str(player_id)][market]
        if groups and not any(float(inputs[g][-1])>0 for g in groups):return None
        base=float(base)
        vector=[base,float(old),float(prior_games),float(recent_volume),float(recent_yards),
                float(team_volume),float(opponent_ratio),float(week)]
        for group in groups:
            values=inputs[group]
            if not isinstance(values,list) or len(values)!=DIMENSIONS[group]:return None
            vector.extend(float(x) for x in values)
        coefficients=[float(x) for x in model["coefficients"]]
        intercept=float(model["intercept"])
        if len(coefficients)!=len(vector) or not all(math.isfinite(x) for x in [*vector,*coefficients,intercept]) or base<0:
            return None
        estimate=max(0.0,intercept+sum(c*x for c,x in zip(coefficients,vector)))
        estimate=min(base*1.25,max(base*0.75,estimate))
        return {"family":FAMILY,"variant":variant,"baseline":round(base,1),
                "candidate":round(estimate,1),"active":False,"research_only":True,
                "trained_season":trained[0],"trained_week":trained[1],
                "holdout_rows":model.get("holdout_rows"),
                "holdout_improvement_pct":model.get("holdout_improvement_pct"),
                "features_used":[g for g in groups if inputs[g][-1]>0]}
    except (KeyError,TypeError,ValueError,OverflowError,IndexError):return None
