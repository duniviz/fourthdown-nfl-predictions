#!/usr/bin/env python3
"""Train count-prop ML calibration from prior completed weeks only.

Only frozen pregame live predictions and their verified results are labels.
Never train on the target game/week; models remain research-only.
"""
import datetime as dt,json,math
from collections import defaultdict
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor,HistGradientBoostingRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/"data"
MAP={"player_pass_completions":"completions","player_rush_attempts":"carries",
     "player_receptions":"receptions"}
def finite(x):
 try:
  v=float(x);return v if math.isfinite(v) else None
 except (ValueError,TypeError):return None
def stamp(s):
 try:return dt.datetime.fromisoformat(str(s).replace("Z","+00:00")).astimezone(dt.timezone.utc)
 except (ValueError,TypeError):return None
def build(now=None):
 now=now or dt.datetime.now(dt.timezone.utc)
 source=json.loads((DATA/"count-projections.json").read_text())
 games=json.loads((DATA/"live-v2.json").read_text())
 results=json.loads((DATA/"player-results.json").read_text()).get("rows",[])
 snaps=json.loads((DATA/"pregame-snapshots.json").read_text()).get("records",[])
 path=DATA/"weekly-shadow-forecasts.json"
 old=json.loads(path.read_text()).get("rows",[]) if path.exists() else []
 indexed={(str(r["game_id"]),str(r["player_id"]),str(r["stat_key"]),str(r["model"])):r for r in old}
 actual={(str(r.get("game_id")),str(r.get("player_id")),str(r.get("stat_key"))):finite(r.get("actual"))
         for r in results if not r.get("dnp") and r.get("played") is not False}
 # Historical labels must be actual archived pregame live forecasts, not a
 # later reconstruction or a current-week prediction.
 history=defaultdict(list)
 for r in old:
  if r.get("model")!="live":continue
  market=MAP.get(r.get("stat_key"))
  if not market:continue
  key=(str(r.get("game_id")),str(r.get("player_id")),market)
  value=actual.get(key);projection=finite(r.get("projection"))
  kick=stamp(r.get("kickoff_utc"));pred=stamp(r.get("predicted_at_utc"))
  try:season,week=map(int,str(r["game_id"]).split("_")[:2])
  except (ValueError,TypeError):continue
  if value is None or projection is None or not kick or not pred or pred>=kick:continue
  history[r["stat_key"]].append((season,week,projection,value))
 generated=stamp(source.get("generated_at_utc"))
 if not generated or generated>now:return old
 game_by_id={str(g.get("game_id")):g for g in games.get("games",[])}
 added=0
 for p in source.get("players",[]):
  market=p.get("market_key")
  if market not in MAP:continue
  game=game_by_id.get(str(p.get("game_id")))
  if not game:continue
  kickoff=stamp(game.get("kickoff_utc"))
  if not kickoff or not generated<kickoff or now>=kickoff:continue
  try:season=int(game["season"]);week=int(game["week"])
  except (ValueError,TypeError,KeyError):continue
  training=[x for x in history[market] if (x[0],x[1])<(season,week)]
  if len(training)<30 or len({(x[0],x[1]) for x in training})<2:continue
  projection=finite(p.get("projection"))
  if projection is None:continue
  x=np.array([[x[2],x[1]] for x in training]);y=np.array([x[3] for x in training])
  models={"ml_count_ridge":make_pipeline(StandardScaler(),Ridge(alpha=100)),
          "ml_count_random_forest":RandomForestRegressor(n_estimators=80,max_depth=4,min_samples_leaf=8,random_state=42,n_jobs=1),
          "ml_count_gradient_boosting":HistGradientBoostingRegressor(max_iter=80,max_leaf_nodes=7,min_samples_leaf=8,l2_regularization=20,random_state=42)}
  for name,model in models.items():
   key=(str(p["game_id"]),str(p["player_id"]),market,name)
   if key in indexed:continue
   pred=float(model.fit(x,y).predict([[projection,week]])[0])
   recorded=dt.datetime.now(dt.timezone.utc)
   if recorded>=kickoff:continue
   indexed[key]={"game_id":key[0],"player_id":key[1],"stat_key":market,
      "model":name,"projection":round(max(0,pred),4),"dk_line":None,
      "kickoff_utc":kickoff.isoformat(),"predicted_at_utc":recorded.isoformat(),"source_forecast_at_utc":generated.isoformat(),
      "source":"historical frozen count projections; prior completed weeks only","actual":None}
   added+=1
 print("New pregame count ML shadow rows:",added)
 return sorted(indexed.values(),key=lambda r:(r["game_id"],r["player_id"],r["stat_key"],r["model"]))
def main():
 rows=build()
 (DATA/"weekly-shadow-forecasts.json").write_text(json.dumps({"schema_version":2,"description":"Frozen pregame ML and research challengers","rows":rows},indent=2)+"\n")
if __name__=="__main__":main()
