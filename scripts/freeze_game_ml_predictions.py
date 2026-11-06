#!/usr/bin/env python3
"""Pregame fitted game-total/margin ML challengers using prior completed scores only."""
import csv,datetime as dt,json,math,pathlib,sys
from collections import defaultdict
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor,HistGradientBoostingRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
ROOT=pathlib.Path(__file__).resolve().parents[1];DATA=ROOT/"data"
def number(x):
 try:
  n=float(x);return n if math.isfinite(n) else None
 except (ValueError,TypeError):return None
def time(x):
 try:return dt.datetime.fromisoformat(str(x).replace("Z","+00:00")).astimezone(dt.timezone.utc)
 except (ValueError,TypeError):return None
def features(history,season,week,home,away):
 def stats(team):
  games=history.get((season,team),[])
  recent=[x for x in games if x[0]<week][-5:]
  if len(recent)<3:return None
  return [sum(x[j] for x in recent)/len(recent) for j in (1,2)]
 h=stats(home);a=stats(away)
 return h+a+[week] if h and a else None
def train(schedule):
 history=defaultdict(list);samples=defaultdict(list);pending=[];current=None
 for r in sorted(schedule,key=lambda r:(int(r.get("season") or 0),int(r.get("week") or 0))):
  try:
   season=int(r["season"]);week=int(r["week"])
   home=r["home_team"];away=r["away_team"]
   hs=number(r.get("home_score"));aws=number(r.get("away_score"))
   if None in (hs,aws) or not home or not away or str(r.get("game_type") or "REG")!="REG":continue
   if current is not None and current!=(season,week):
    for key,val in pending:history[key].append(val)
    pending=[]
   current=(season,week)
   x=features(history,season,week,home,away)
   if season<=2025 and x:
    samples["game_total"].append((x,hs+aws))
    samples["game_margin_home"].append((x,hs-aws))
   pending.extend([((season,home),(week,hs,aws)),((season,away),(week,aws,hs))])
  except (KeyError,ValueError,TypeError):continue
 for key,val in pending:history[key].append(val)
 models={}
 for market,rows in samples.items():
  if len(rows)<150:continue
  x=np.array([r[0] for r in rows]);y=np.array([r[1] for r in rows])
  models[market]={
   "ml_ridge":make_pipeline(StandardScaler(),Ridge(alpha=100)),
   "ml_random_forest":RandomForestRegressor(n_estimators=100,max_depth=5,min_samples_leaf=12,random_state=42,n_jobs=1),
   "ml_gradient_boosting":HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=9,min_samples_leaf=20,l2_regularization=20,random_state=42)}
  for model in models[market].values():model.fit(x,y)
 return history,models
def less_shrinkage_margin(history,season,week,home,away):
 """Research-only prior-week 50/50 blend of shrunk and raw team scoring."""
 teams={}
 for (year,team),games in history.items():
  if year!=season:continue
  past=[g for g in games if g[0]<week]
  if len(past)>=3:teams[team]=past
 if home not in teams or away not in teams:return None
 all_points=[g[1] for games in teams.values() for g in games]
 if not all_points:return None
 league=sum(all_points)/len(all_points)
 def rate(team,index):
  games=teams[team];raw=sum(g[index] for g in games)/len(games)
  weight=len(games)/(len(games)+5)
  shrunk=weight*raw+(1-weight)*league
  return .5*shrunk+.5*raw
 return .5*(rate(home,1)+rate(away,2))-.5*(rate(away,1)+rate(home,2))+2

def main():
 with open(sys.argv[1],newline="") as f:history,models=train(csv.DictReader(f))
 live=json.loads((DATA/"live-v2.json").read_text());created=time(live.get("generated_at_utc"))
 now=dt.datetime.now(dt.timezone.utc);path=DATA/"weekly-shadow-forecasts.json"
 existing=json.loads(path.read_text()).get("rows",[]) if path.exists() else []
 indexed={(r["game_id"],r["player_id"],r["stat_key"],r["model"]):r for r in existing}
 if created and created<=now:
  for game in live.get("games",[]):
   kickoff=time(game.get("kickoff_utc"))
   if not kickoff or not created<kickoff or not now<kickoff:continue
   x=features(history,int(game["season"]),int(game["week"]),game["home"],game["away"])
   if x is None:continue
   # Freeze the incumbent on the same slate and timestamp as challengers.
   incumbent={"game_total":number(game.get("projected_total")),
              "game_margin_home":number(game.get("projected_margin_home"))}
   for market,value in incumbent.items():
    key=(str(game["game_id"]),"GAME",market,"live")
    if value is not None and key not in indexed:
     indexed[key]={"game_id":key[0],"player_id":"GAME","stat_key":market,
       "model":"live","projection":round(value,4),"dk_line":None,
       "kickoff_utc":kickoff.isoformat(),"predicted_at_utc":created.isoformat(),
       "source":"frozen production game projection","actual":None}
   margin=less_shrinkage_margin(history,int(game["season"]),int(game["week"]),game["home"],game["away"])
   if margin is not None:
    key=(str(game["game_id"]),"GAME","game_margin_home","less_shrinkage")
    if key not in indexed:
     indexed[key]={"game_id":key[0],"player_id":"GAME","stat_key":"game_margin_home",
       "model":"less_shrinkage","projection":round(margin,4),"dk_line":None,
       "kickoff_utc":kickoff.isoformat(),"predicted_at_utc":created.isoformat(),
       "source":"prior-week 50/50 shrunk/raw scoring challenger","actual":None}
   for market,modelset in models.items():
    for name,model in modelset.items():
     key=(str(game["game_id"]),"GAME",market,name)
     if key in indexed:continue
     pred=float(model.predict(np.array([x]))[0])
     indexed[key]={"game_id":key[0],"player_id":"GAME","stat_key":market,"model":name,
       "projection":round(max(0,pred),4) if market=="game_total" else round(pred,4),
       "dk_line":None,"kickoff_utc":kickoff.isoformat(),"predicted_at_utc":created.isoformat(),
       "source":"fitted historical prior-week score features","actual":None}
 path.write_text(json.dumps({"schema_version":2,"description":"Frozen pregame research challenger forecasts","rows":sorted(indexed.values(),key=lambda r:(r["game_id"],r["player_id"],r["stat_key"],r["model"]))},indent=2)+"\n")
 print("Frozen game ML rows:",sum(r["model"].startswith("ml_") and r["player_id"]=="GAME" for r in indexed.values()))
if __name__=="__main__":main()
