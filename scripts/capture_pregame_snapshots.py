#!/usr/bin/env python3
"""Persist latest strictly pre-kickoff player projections and verified DK quotes.
Uses only published source timestamps; never backfills post-kickoff estimates.
"""
import json, pathlib, datetime, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
def read(name):
 try:return json.loads((DATA/name).read_text())
 except (OSError,ValueError):return {}
def dt(s):
 try:return datetime.datetime.fromisoformat(str(s).replace("Z","+00:00")).astimezone(datetime.timezone.utc)
 except (ValueError,TypeError,AttributeError):return None
def schedule():
 url="https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=300"
 with urllib.request.urlopen(url,timeout=20) as response: events=json.load(response).get("events",[])
 result={}
 for e in events:
  start=dt(e.get("date"))
  teams=[x.get("team",{}).get("abbreviation","") for x in e.get("competitions",[{}])[0].get("competitors",[])]
  if start and len(teams)==2:
   for a in teams:
    for b in teams:
     if a!=b:result[(a,b)]=start
 return result
def capture(existing,projections,quotes,games,now):
 records={tuple(str(r.get(k,"")) for k in ("game_id","player_id","market")):r for r in existing}
 for p in projections:
  team=p.get("team","");opp=p.get("opponent","")
  kickoff=games.get((team,opp))
  generated=dt(p.get("generated_at_utc"))
  if not kickoff or not generated or generated>=kickoff or now>=kickoff:continue
  market=p.get("market_key") or p.get("market")
  if not p.get("game_id") or not p.get("player_id") or not market:continue
  try: projection=float(p["projection"])
  except (TypeError,ValueError,KeyError):continue
  matching=[]
  for q in quotes:
   qtime=dt(q.get("captured_at") or q.get("updated_at_utc") or q.get("timestamp"))
   if not qtime or qtime>=kickoff or qtime>now:continue
   if str(q.get("game_id"))!=str(p["game_id"]):continue
   if str(q.get("market_key") or q.get("market"))!=str(market):continue
   if str(q.get("player_id") or "")!=str(p["player_id"]):continue
   matching.append((qtime,q))
  matching.sort(key=lambda x:x[0],reverse=True)
  quote=matching[0][1] if matching else {}
  try:line=float(quote.get("line") if quote.get("line") is not None else quote.get("dk_line"))
  except (TypeError,ValueError):line=None
  key=(str(p["game_id"]),str(p["player_id"]),str(market))
  previous=records.get(key)
  # Never regress a captured projection, even when the feed is stale.\n  if previous and dt(previous.get("captured_at")) and dt(previous["captured_at"])>=generated:continue
  records[key]={"game_id":p["game_id"],"player_id":p["player_id"],"player":p.get("player"),
    "team":team,"market":market,"projection":projection,"dk_line":line,
    "captured_at":generated.isoformat(),"dk_captured_at":(matching[0][0].isoformat() if matching else None),
    "kickoff":kickoff.isoformat()}
 return sorted(records.values(),key=lambda r:(str(r["game_id"]),str(r["player_id"]),str(r["market"])))
def main():
 now=datetime.datetime.now(datetime.timezone.utc)
 games=schedule()
 source=read("count-projections.json")
 generated=source.get("generated_at_utc")
 projections=[dict(p,generated_at_utc=generated) for p in source.get("players",[])]
 odds=read("dk-odds.json")
 quotes=odds.get("rows",[])
 archive=read("dk-line-history.json")
 quotes+=archive.get("rows",[])
 dest=DATA/"pregame-snapshots.json"
 old=read("pregame-snapshots.json").get("records",[])
 rows=capture(old,projections,quotes,games,now)
 payload={"schema_version":1,"description":"Immutable last available pre-kickoff snapshots; missing lines are null","records":rows}
 dest.write_text(json.dumps(payload,indent=2)+"\n")
 print(f"Snapshots: {len(rows)} (previous {len(old)})")
if __name__=="__main__":main()
