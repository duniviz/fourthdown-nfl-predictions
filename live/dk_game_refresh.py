"""Refresh verified DraftKings game spreads/totals from ParlayAPI.

One API call per forecast run. Fail closed and preserve previous data when no
valid markets are returned. No game/player props requests are duplicated.
"""
import json
import math
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from live.game_pregame_observations import dt

OUT=Path("data/dk-game-odds.json")
HISTORY=Path("data/dk-game-line-history.json")
BASE="https://parlay-api.com/v1/sports/americanfootball_nfl/odds"

def finite(value):
    try:
        v=float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None

def parse(payload, now):
    events=payload if isinstance(payload,list) else next(
        (payload[k] for k in ("data","events","results","rows") if isinstance(payload.get(k),list)), [])
    out=[]
    for event in events:
        if not isinstance(event,dict):
            continue
        kickoff=dt(event.get("commence_time"))
        if not kickoff or kickoff<=now:
            continue
        home,away=event.get("home_team"),event.get("away_team")
        books=event.get("bookmakers",[])
        if not home or not away or not isinstance(books,list):
            continue
        for book in books:
            if not isinstance(book,dict) or str(book.get("key","")).lower()!="draftkings":
                continue
            updated=dt(book.get("last_update"))
            if not updated or updated>now or updated>=kickoff:
                continue
            markets={m.get("key"):m for m in book.get("markets",[]) if isinstance(m,dict)}
            spread=next((finite(x.get("point")) for x in markets.get("spreads",{}).get("outcomes",[])
                         if isinstance(x,dict) and x.get("name")==home),None)
            total=next((finite(x.get("point")) for x in markets.get("totals",{}).get("outcomes",[])
                        if isinstance(x,dict) and str(x.get("name","")).lower()=="over"),None)
            if spread is None and total is None:
                continue
            out.append({"game_id":event.get("id"),"home_team":home,"away_team":away,
                        "commence_time":kickoff.isoformat(),"bookmaker":"draftkings",
                        "home_spread":spread,"total":total,"updated_at_utc":updated.isoformat()})
    return out

def main():
    key=os.environ.get("PARLAY_API_KEY","").strip()
    if not key:
        print("PARLAY_API_KEY missing; preserving existing game odds")
        return
    now=datetime.now(timezone.utc)
    params=urllib.parse.urlencode({"bookmakers":"draftkings","regions":"us",
        "markets":"spreads,totals","oddsFormat":"american","dateFormat":"iso"})
    req=urllib.request.Request(BASE+"?"+params,headers={"X-API-Key":key,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=35) as response:
        payload=json.load(response)
    rows=parse(payload,now)
    if not rows:
        print("No valid DraftKings game odds returned; retaining previous files")
        return
    # Map the provider's full team names to published NFL team abbreviations,
    # never infer from substrings or fabricate a game match.
    live=json.loads(Path("data/live-v2.json").read_text())
    mapped=[]
    for row in rows:
        match=next((g for g in live.get("games",[]) if
            g.get("home_team")==row["home_team"] and g.get("away_team")==row["away_team"]
            and dt(g.get("kickoff_utc"))==dt(row["commence_time"])),None)
        if match is None:
            # Published games currently store abbreviations, so use the known
            # team names already present in the existing DK odds file.
            continue
        mapped.append({**row,"home":match["home"],"away":match["away"]})
    # Existing odds provide an explicit full-name -> abbreviation mapping.
    previous=json.loads(OUT.read_text()) if OUT.exists() else {}
    names={}
    for row in previous.get("games",[]):
        if row.get("home_team") and row.get("home"):
            names[row["home_team"]]=row["home"]
        if row.get("away_team") and row.get("away"):
            names[row["away_team"]]=row["away"]
    for row in rows:
        if row["home_team"] not in names or row["away_team"] not in names:
            continue
        item={**row,"home":names[row["home_team"]],"away":names[row["away_team"]]}
        if any(g.get("home")==item["home"] and g.get("away")==item["away"] and
               dt(g.get("kickoff_utc"))==dt(item["commence_time"]) for g in live.get("games",[])):
            mapped.append(item)
    mapped=list({(x["home"],x["away"],x["commence_time"]):x for x in mapped}.values())
    if not mapped:
        print("No odds matched published games; retaining existing files")
        return
    history=json.loads(HISTORY.read_text()) if HISTORY.exists() else {"schema_version":1,"games":{}}
    games=history.setdefault("games",{})
    for row in mapped:
        k="|".join((row["away"],row["home"],row["commence_time"]))
        entry={"captured_at_utc":row["updated_at_utc"],
               "home_spread":row["home_spread"],"total":row["total"]}
        prior=games.setdefault(k,[])
        if entry not in prior:
            prior.append(entry)
    OUT.write_text(json.dumps({"source":"ParlayAPI","bookmaker":"draftkings",
        "snapshot_date_utc":now.isoformat(),"games":mapped},indent=2)+"\n")
    HISTORY.write_text(json.dumps(history,indent=2)+"\n")
    print(f"Updated {len(mapped)} verified DraftKings game odds")

if __name__=="__main__":
    main()
