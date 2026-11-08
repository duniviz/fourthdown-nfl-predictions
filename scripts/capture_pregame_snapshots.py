#!/usr/bin/env python3
"""Persist latest strictly pre-kickoff player projections and verified DK quotes.
Uses only published source timestamps; never backfills post-kickoff estimates.
"""
import json, pathlib, datetime, urllib.request, sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from live.dk_identity import QuoteIndex, market as canonical_market, finite
from live.game_pregame_observations import dt
from tools.weather_adjustment_template import scenario, adjusted_projection
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
def read(name):
 path=DATA/name
 return json.loads(path.read_text()) if path.exists() else {}

def capture(existing,projections,quotes,games,now,weather_feed=None):
 records={tuple(str(r.get(k,"")) for k in ("game_id","player_id","market")):r for r in existing}
 index=QuoteIndex(quotes,now)
 from collections import defaultdict
 from live.dk_identity import norm
 names=defaultdict(set)
 for item in projections:
  k=(norm(item.get("player")),canonical_market(item.get("market_key")),str(item.get("game_id")))
  names[k].add(str(item.get("player_id")))
 legacy={}
 for q in quotes:
  stamp=dt(q.get("captured_at") or q.get("updated_at_utc") or q.get("timestamp"))
  if stamp and q.get("player_id") and q.get("game_id") and q.get("bookmaker","draftkings")=="draftkings":
   legacy.setdefault((str(q["game_id"]),str(q["player_id"]),canonical_market(q.get("market_key") or q.get("market"))),[]).append((stamp,q))
 for p in projections:
  team=p.get("team","");opp=p.get("opponent","")
  kickoff=games.get(p.get("game_id")) or games.get((team,opp))
  generated=dt(p.get("generated_at_utc"))
  if not kickoff or not generated or generated>=kickoff or now>=kickoff or generated>now:continue
  market=p.get("market_key") or p.get("market")
  if not p.get("game_id") or not p.get("player_id") or not market:continue
  projection=finite(p.get("projection"))
  if projection is None:continue
  name_key=(norm(p.get("player")),canonical_market(market),str(p.get("game_id")))
  found=index.find(p,kickoff) if len(names[name_key])==1 else None
  matching=[(t,q) for t,q in legacy.get((str(p["game_id"]),str(p["player_id"]),canonical_market(market)),[])
            if t<=now and t<kickoff and (not q.get("commence_time") or dt(q["commence_time"])==kickoff)
            and finite(q.get("line",q.get("dk_line"))) is not None]
  if found:matching.append(found[:2])
  matching.sort(key=lambda x:x[0],reverse=True)
  quote=matching[0][1] if matching else {}
  line=finite(quote.get("line",quote.get("dk_line")))
  key=(str(p["game_id"]),str(p["player_id"]),str(market))
  wx=None
  if weather_feed:
   game_weather=weather_feed.get('games',{}).get(str(p['game_id']),{})
   weather_time=dt(weather_feed.get('generated_at_utc'))
   if (game_weather.get('status')=='forecast' and weather_time and weather_time<=now and weather_time<kickoff):
    try:
     import re
     wind=re.search(r'\d+(?:\.\d+)?',str(game_weather.get('wind_speed','')))
     temp=float(game_weather['temperature_f'])
     chance=float(game_weather['precipitation_probability'])
     conditions=str(game_weather.get('conditions','')).lower()
     heavy=chance>=60 and any(x in conditions for x in ('rain','snow','sleet','storm','shower'))
     wx=scenario(float(wind.group()) if wind else None,temp,heavy,'outdoor')
    except (TypeError,ValueError,KeyError,AttributeError):pass
  weather_projection=adjusted_projection(str(market),projection,wx) if wx else None
  previous=records.get(key)
  if previous and dt(previous.get("kickoff")) != kickoff:
   old_kickoff=dt(previous.get("kickoff"))
   if not old_kickoff or now>=old_kickoff:
    continue
   # Old quote belongs to the previous scheduled time. Keep that observation
   # in player-history and require a quote for the revised kickoff.
   previous=None
  # Never regress a captured projection, even when the feed is stale.
  if previous:
   prev_time=dt(previous.get("captured_at"))
   prev_dk_time=dt(previous.get("dk_captured_at"))
   next_dk_time=matching[0][0] if matching else None
   # Keep latest pregame projection and DK line independently.
   if prev_time and prev_time>=generated:
    projection=previous.get("projection")
    generated=prev_time
   if prev_dk_time and (not next_dk_time or prev_dk_time>=next_dk_time):
    line=previous.get("dk_line")
    next_dk_time=prev_dk_time
   dk_time=next_dk_time.isoformat() if next_dk_time else None
  else:
   dk_time=matching[0][0].isoformat() if matching else None
  # Preserve the weather value from the most recent immutable pregame capture.
  if previous and prev_time and prev_time>=dt(p.get('generated_at_utc')):
   weather_projection=previous.get('weather_projection')
   wx=None
  records[key]={"game_id":p["game_id"],"player_id":p["player_id"],"player":p.get("player"),
    "team":team,"opponent":opp,"market":market,"projection":projection,"dk_line":line,
    "captured_at":generated.isoformat(),"dk_captured_at":dk_time,
    "weather_projection":weather_projection,
    "weather_version":"weather-template-v1" if weather_projection is not None else None,
    "kickoff":kickoff.isoformat(),"saved_at_utc":now.isoformat()}
 return sorted(records.values(),key=lambda r:(str(r["game_id"]),str(r["player_id"]),str(r["market"])))
STATS = {"player_rec_yds":"receiving_yards","player_rush_yds":"rushing_yards","player_pass_yds":"passing_yards",
         "player_pass_attempts":"attempts","player_pass_completions":"completions","player_rush_attempts":"carries",
         "player_receptions":"receptions"}
LABELS = {"completions":"Pass completions","attempts":"Pass attempts","carries":"Rush attempts","receptions":"Receptions",
          "passing_yards":"Passing yards","rushing_yards":"Rushing yards","receiving_yards":"Receiving yards"}

def collect(data, now, game_ids=None):
 global DATA
 DATA=data
 schedule={g["game_id"]:dt(g.get("kickoff_utc")) for g in read("live-v2.json").get("games",[])
           if game_ids is None or g["game_id"] in game_ids}
 if not schedule:raise ValueError("No scheduled games to capture")
 sources={}
 for filename in ("player-research.json","count-projections.json"):
  feed=read(filename)
  for p in feed.get("players",[]):
   mk=canonical_market(p.get("market_key"))
   if mk not in STATS or not p.get("player_id"):continue
   key=(p.get("game_id"),p["player_id"],mk)
   sources[key]={**p,"market_key":mk,"stat_key":STATS[mk],"market":LABELS[STATS[mk]],"generated_at_utc":feed.get("generated_at_utc")}
 odds=read("dk-odds.json")
 quotes=odds.get("rows",[]) if odds.get("bookmaker")=="draftkings" else []
 snapshots=read("pregame-snapshots.json")
 old=snapshots.get("records",[])
 rows=capture(old,sources.values(),quotes,schedule,now,read("weather.json"))
 if len(rows)<len(old):raise ValueError("Refusing to discard frozen records")
 if rows!=old:
  (data/"pregame-snapshots.json").write_text(json.dumps({**snapshots,"schema_version":2,"records":rows},indent=2)+"\n")
 history=read("player-history.json")
 players=history.get("players",[])
 def observation(x):
  return (x.get("game_id"),x.get("player_id"),x.get("stat_key"),dt(x.get("forecast_captured_at_utc")),dt(x.get("dk_quote_time")))
 seen={observation(x) for x in players}
 added=0
 for row in rows:
  key=(row["game_id"],row["player_id"],row["market"])
  p=sources.get(key)
  if not p or schedule.get(key[0])!=dt(row["kickoff"]) or not now<dt(row["kickoff"]):continue
  if dt(row["captured_at"])!=dt(p.get("generated_at_utc")):continue
  line=row["dk_line"]
  side=None if line is None else ("OVER" if row["projection"]>line else "UNDER" if row["projection"]<line else "NO_PICK")
  record={**p,"kickoff_utc":row["kickoff"],"forecast_captured_at_utc":row["captured_at"],
          "dk_quote_time":row["dk_captured_at"],"dk_line":line,"saved_at_utc":now.isoformat(),
          "recommended_side":side,"snapshot_source":"matched_published_pregame_card"}
  if observation(record) not in seen:
   seen.add(observation(record))
   players.append(record)
   added+=1
 if added:
  (data/"player-history.json").write_text(json.dumps({**history,"players":players},indent=2)+"\n")
 print(f"Frozen player records: {len(rows)}, new observations: {added}")
 return rows

def main():
 collect(DATA,datetime.datetime.now(datetime.timezone.utc))
if __name__=="__main__":main()
