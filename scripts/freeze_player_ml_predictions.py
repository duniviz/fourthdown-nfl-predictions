#!/usr/bin/env python3
"""Freeze genuinely fitted yardage ML forecasts before kickoff. Research only."""
import csv,datetime as dt,json,math,pathlib
from collections import defaultdict
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor,HistGradientBoostingRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
ROOT=pathlib.Path(__file__).resolve().parents[1];DATA=ROOT/"data"
UTC=dt.timezone.utc
def stamp(x):
 try:return dt.datetime.fromisoformat(str(x).replace("Z","+00:00")).astimezone(UTC)
 except (TypeError,ValueError):return None
def finite(x):
 try:
  n=float(x);return n if math.isfinite(n) else None
 except (TypeError,ValueError):return None
def fit(rows):
 grouped=defaultdict(list)
 for r in rows:
  if r.get("market") not in ("passing_yards","rushing_yards","receiving_yards"):continue
  try:
   season=int(r["season"]);week=int(r["week"])
   old=finite(r["old"]);new=finite(r["new"]);actual=finite(r["actual"])
   if season>=2026 or None in (old,new,actual) or min(old,new,actual)<0:continue
   grouped[r["market"]].append(([new,week],actual))
  except (KeyError,ValueError,TypeError):continue
 models={}
 for market,items in grouped.items():
  if len(items)<100:continue
  x=np.asarray([i[0] for i in items]);y=np.asarray([i[1] for i in items])
  models[market]={
   "ridge":make_pipeline(StandardScaler(),Ridge(alpha=100)),
   "random_forest":RandomForestRegressor(n_estimators=100,max_depth=5,min_samples_leaf=15,random_state=42,n_jobs=1),
   "gradient_boosting":HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=9,min_samples_leaf=25,l2_regularization=20,random_state=42)}
  for m in models[market].values():m.fit(x,y)
 return models
def build(now=None):
 now=now or dt.datetime.now(UTC)
 with (DATA/"backtests/player-predictions.csv").open(newline="") as f:models=fit(csv.DictReader(f))
 games=json.loads((DATA/"live-v2.json").read_text());desk=json.loads((DATA/"research-prop-desk.json").read_text())
 gs=stamp(games.get("generated_at_utc"));ds=stamp(desk.get("generated_at_utc"))
 archive=DATA/"weekly-shadow-forecasts.json"
 previous=json.loads(archive.read_text()) if archive.exists() else {"rows":[]}
 indexed={(r["game_id"],r["player_id"],r["stat_key"],r["model"]):r for r in previous.get("rows",[])}
 if not ds or not gs or ds>now or gs>now:return list(indexed.values())
 for p in desk.get("comparisons",[]):
  market=p.get("market");modelset=models.get(market)
  if not modelset or not p.get("player_id"):continue
  g=next((g for g in games.get("games",[]) if {g.get("home"),g.get("away")}=={p.get("team"),p.get("opponent")}),None)
  if not g:continue
  kickoff=stamp(g.get("kickoff_utc"))
  if not kickoff or not (ds<kickoff and gs<kickoff and now<kickoff):continue
  live=finite(p.get("projected_yards"))
  if live is None or live<0:continue
  # Train and infer on the same available features: pregame baseline and week.
  features=np.asarray([[live,int(g["week"])]])
  for name,model in modelset.items():
   key=(str(g["game_id"]),str(p["player_id"]),market,"ml_"+name)
   if key in indexed:continue
   pred=float(model.predict(features)[0])
   recorded=dt.datetime.now(UTC)
   if recorded>=kickoff:continue
   indexed[key]={"game_id":key[0],"player_id":key[1],"stat_key":market,"model":key[3],
    "projection":round(max(0,pred),4),"dk_line":None,"kickoff_utc":kickoff.isoformat(),
    "predicted_at_utc":recorded.isoformat(),"source_forecast_at_utc":ds.isoformat(),"source":"fitted historical 2024-2025 ML, baseline/week pregame inputs","actual":None}
 return sorted(indexed.values(),key=lambda r:(r["game_id"],r["player_id"],r["stat_key"],r["model"]))
def main():
 rows=build();path=DATA/"weekly-shadow-forecasts.json"
 path.write_text(json.dumps({"schema_version":2,"description":"Frozen pregame research challenger forecasts","rows":rows},indent=2)+"\n")
 print("Frozen ML rows:",sum(r["model"].startswith("ml_") for r in rows))
if __name__=="__main__":main()
