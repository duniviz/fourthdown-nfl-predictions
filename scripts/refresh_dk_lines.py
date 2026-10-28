#!/usr/bin/env python3
"""Refresh only verified DraftKings NFL game odds and player props from ParlayAPI."""
import datetime as dt
import json
import os
import pathlib
import urllib.parse
import urllib.request

BASE = "https://parlay-api.com/v1/sports/americanfootball_nfl"
ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
KEY = os.environ.get("PARLAYAPI_KEY", "").strip()
if not KEY:
    raise SystemExit("PARLAYAPI_KEY secret missing; refusing to overwrite saved odds")
NOW = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
ABBR = {
"Arizona Cardinals":"ARI","Atlanta Falcons":"ATL","Baltimore Ravens":"BAL",
"Buffalo Bills":"BUF","Carolina Panthers":"CAR","Chicago Bears":"CHI",
"Cincinnati Bengals":"CIN","Cleveland Browns":"CLE","Dallas Cowboys":"DAL",
"Denver Broncos":"DEN","Detroit Lions":"DET","Green Bay Packers":"GB",
"Houston Texans":"HOU","Indianapolis Colts":"IND","Jacksonville Jaguars":"JAX",
"Kansas City Chiefs":"KC","Las Vegas Raiders":"LV","Los Angeles Chargers":"LAC",
"Los Angeles Rams":"LA","Miami Dolphins":"MIA","Minnesota Vikings":"MIN",
"New England Patriots":"NE","New Orleans Saints":"NO","New York Giants":"NYG",
"New York Jets":"NYJ","Philadelphia Eagles":"PHI","Pittsburgh Steelers":"PIT",
"San Francisco 49ers":"SF","Seattle Seahawks":"SEA","Tampa Bay Buccaneers":"TB",
"Tennessee Titans":"TEN","Washington Commanders":"WAS"
}
def fetch(path,params):
    url=BASE+path+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"X-API-Key":KEY,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=35) as res:
        return json.load(res),dict(res.headers)
def rows(payload):
    if isinstance(payload,list):return payload
    if isinstance(payload,dict):
        for key in ("rows","data","events","results"):
            if isinstance(payload.get(key),list):return payload[key]
    return []
def time_iso(v):
    if isinstance(v,(int,float)):
        return dt.datetime.fromtimestamp(v/(1000 if v>1e11 else 1),dt.timezone.utc).isoformat().replace("+00:00","Z")
    return v if isinstance(v,str) else None
def upcoming(v):
    try:return dt.datetime.fromisoformat(time_iso(v).replace("Z","+00:00"))>dt.datetime.now(dt.timezone.utc)
    except (ValueError,AttributeError,TypeError):return False
def save(path,obj):
    dest=DATA/path
    dest.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

games_raw,_=fetch("/odds",{"bookmakers":"draftkings","regions":"us","markets":"spreads,totals","oddsFormat":"american","dateFormat":"iso"})
games=[]
for event in rows(games_raw):
    home=event.get("home_team");away=event.get("away_team");kick=event.get("commence_time")
    if home not in ABBR or away not in ABBR or not upcoming(kick):continue
    books=event.get("bookmakers",[])
    if not isinstance(books,list):continue
    book=next((b for b in books if str(b.get("key","")).lower()=="draftkings"),None)
    if not book:continue
    markets={m.get("key"):m for m in book.get("markets",[]) if isinstance(m,dict)}
    spread=next((x.get("point") for x in markets.get("spreads",{}).get("outcomes",[]) if x.get("name")==home),None)
    total=next((x.get("point") for x in markets.get("totals",{}).get("outcomes",[]) if str(x.get("name","")).lower()=="over"),None)
    if spread is None and total is None:continue
    kickoff=dt.datetime.fromisoformat(time_iso(kick).replace("Z","+00:00"))
    # NFL season is calendar year for fall games; early January belongs to previous season.
    season=kickoff.year-(1 if kickoff.month<=2 else 0)
    # Match against existing published game IDs, rather than guessing NFL week.
    existing=json.loads((DATA/"live-v2.json").read_text(encoding="utf-8")) if (DATA/"live-v2.json").exists() else {}
    match=next((g for g in existing.get("games",[]) if g.get("home")==ABBR[home] and g.get("away")==ABBR[away] and abs((dt.datetime.fromisoformat(g["kickoff_utc"].replace("Z","+00:00"))-kickoff).total_seconds())<43200),None)
    if not match:continue
    games.append({"game_id":match["game_id"],"home":ABBR[home],"away":ABBR[away],"bookmaker":"draftkings","home_spread":spread,"total":total,"updated_at_utc":time_iso(book.get("last_update")) or NOW})
if games:
    save("dk-game-odds.json",{"generated_at_utc":NOW,"source":"ParlayAPI","bookmaker":"draftkings","games":games})
else:print("No matched DK game odds; retaining previous game file")

props_raw,headers=fetch("/props",{"bookmakers":"draftkings","limit":10000})
props=[]
for p in rows(props_raw):
    if str(p.get("bookmaker","")).lower()!="draftkings" or p.get("period","FULL") not in ("FULL",None):continue
    if not upcoming(p.get("commence_time")):continue
    if not p.get("player") or not p.get("market_key") or p.get("line") is None:continue
    props.append({k:p.get(k) for k in ("player","market_key","line","over_price","under_price","yes_price","no_price","home_team","away_team","commence_time","last_update","age_seconds")})
if props:
    save("dk-odds.json",{"generated_at_utc":NOW,"source":"ParlayAPI","bookmaker":"draftkings","rows":props})
else:print("No eligible DK player props; retaining previous player file")
print(f"DK odds refresh complete: {len(games)} matched games, {len(props)} player props")
