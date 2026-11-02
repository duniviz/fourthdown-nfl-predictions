#!/usr/bin/env python3
"""Build verified per-game NFL count prop trends from ESPN final box scores."""
import datetime as dt
import json
import pathlib
import re
import urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
MARKETS={"passing":{"player_pass_completions":("C/ATT",0),"player_pass_attempts":("C/ATT",1),"player_pass_yds":("YDS",0)},"rushing":{"player_rush_attempts":("CAR",0),"player_rush_yds":("YDS",0)},"receiving":{"player_receptions":("REC",0),"player_rec_yds":("YDS",0)}}
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":"FOURTHDOWN-trends/1.0"})
 with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
def norm(s):return re.sub(r"[^a-z0-9]","",str(s or "").lower())
def read(p):
 try:return json.loads((DATA/p).read_text())
 except (OSError,ValueError):return {}
def parse(category,athlete):
 labels=[str(x).upper() for x in category.get("labels",[])]
 stats=athlete.get("stats") or []
 out={}
 for market,(label,part) in MARKETS.get(str(category.get("name","")).lower(),{}).items():
  if label not in labels:continue
  idx=labels.index(label)
  if idx>=len(stats):continue
  try:
   value=str(stats[idx]).split("/")
   out[market]=float(value[part])
  except (ValueError,IndexError,TypeError):continue
 return out
def main():
 projections=read("count-projections.json")
 players=projections.get("players",[])
 research=read("player-research.json")
 players+=research.get("players",[])
 desk=read("research-prop-desk.json")
 yard_markets={"passing_yards":"player_pass_yds","rushing_yards":"player_rush_yds","receiving_yards":"player_rec_yds"}
 for item in desk.get("comparisons",[]):
  market=yard_markets.get(item.get("market"))
  if market and item.get("player_name") and item.get("player_id"):
   players.append({"player":item["player_name"],"player_id":item["player_id"],"market_key":market})
 if not players:raise SystemExit("No player projections")
 season=int(projections.get("season",dt.datetime.now().year))
 week=int(projections.get("week",1))
 targets={norm(p.get("player")) for p in players}
 history={}
 for w in range(1,week):
  try:board=get(f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={season}&seasontype=2&week={w}&limit=100")
  except Exception as e:print("Scoreboard unavailable",w,e);continue
  for event in board.get("events",[]):
   if not event.get("status",{}).get("type",{}).get("completed"):continue
   try:detail=get(f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={event['id']}")
   except Exception as e:print("Summary unavailable",event.get("id"),e);continue
   for side in detail.get("boxscore",{}).get("players",[]):
    for category in side.get("statistics",[]):
     for athlete in category.get("athletes",[]):
      person=athlete.get("athlete",{})
      key=norm(person.get("displayName"))
      if key not in targets:continue
      for market,value in parse(category,athlete).items():
       history.setdefault((key,market),[]).append({"week":w,"actual":value,"opponent":None})
 out={}
 by_name={}
 for (name,market),games in history.items():
  rows=sorted(games,key=lambda x:x["week"])
  if rows:by_name[name+"|"+market]={"games":rows,"sample_size":len(rows)}
 for p in players:
  key=(norm(p.get("player")),p.get("market_key"))
  rows=sorted(history.get(key,[]),key=lambda x:x["week"])[-5:]
  if rows:out[str(p.get("player_id"))+"|"+str(p.get("market_key"))]={"games":rows,"sample_size":len(rows)}
 payload={"source":"ESPN final box scores","season":season,"through_week":week-1,"updated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"players":out,"by_name":by_name}
 (DATA/"player-recent-games.json").write_text(json.dumps(payload,indent=2)+"\n")
 print("Players with verified recent games:",len(out))
if __name__=="__main__":main()
