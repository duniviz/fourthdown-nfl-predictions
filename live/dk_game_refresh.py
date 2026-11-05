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

def response_diagnostics(payload, now):
    """Summarize response shape and rejection reasons without logging odds or secrets."""
    if isinstance(payload, list):
        events=payload
        shape="list"
    elif isinstance(payload, dict):
        shape="dict"
        events=next((payload[k] for k in ("data","events","results","rows")
                     if isinstance(payload.get(k),list)),None)
        if events is None:
            print("DK response diagnostic: object keys="+",".join(sorted(str(k) for k in payload)[:20]))
            return
    else:
        print("DK response diagnostic: unexpected top-level type="+type(payload).__name__)
        return
    counts={"invalid_event":0,"missing_or_past_kickoff":0,
            "missing_teams_or_books":0,"no_draftkings_book":0,
            "invalid_book_timestamp":0,"no_usable_spread_or_total":0,
            "eligible":0}
    for event in events:
        if not isinstance(event,dict):
            counts["invalid_event"]+=1
            continue
        kickoff=dt(event.get("commence_time"))
        if not kickoff or kickoff<=now:
            counts["missing_or_past_kickoff"]+=1
            continue
        books=event.get("bookmakers")
        if not event.get("home_team") or not event.get("away_team") or not isinstance(books,list):
            counts["missing_teams_or_books"]+=1
            continue
        dk=[b for b in books if isinstance(b,dict) and str(b.get("key","")).lower()=="draftkings"]
        if not dk:
            counts["no_draftkings_book"]+=1
            continue
        valid=[b for b in dk if (lambda t: t is not None and t<=now and t<kickoff)(dt(b.get("last_update")))]
        if not valid:
            counts["invalid_book_timestamp"]+=1
            continue
        if not any(isinstance(m,dict) and m.get("key") in ("spreads","totals")
                   and isinstance(m.get("outcomes"),list)
                   for b in valid for m in b.get("markets",[])):
            counts["no_usable_spread_or_total"]+=1
            continue
        counts["eligible"]+=1
    print(f"DK response diagnostic: shape={shape}, events={len(events)}, "+", ".join(f"{k}={v}" for k,v in counts.items()))
    if events and isinstance(events[0],dict):
        print("DK response diagnostic: event field names="+",".join(sorted(str(k) for k in events[0])[:20]))

def main():
    key=os.environ.get("PARLAY_API_KEY","").strip()
    if not key:
        raise RuntimeError("PARLAY_API_KEY missing; cannot refresh DraftKings game odds")
    now=datetime.now(timezone.utc)
    params=urllib.parse.urlencode({"bookmakers":"draftkings","regions":"us",
        "markets":"spreads,totals","oddsFormat":"american","dateFormat":"iso"})
    req=urllib.request.Request(BASE+"?"+params,headers={"X-API-Key":key,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=35) as response:
        payload=json.load(response)
    response_diagnostics(payload,now)
    rows=parse(payload,now)
    if not rows:
        print("DK game odds: zero eligible upcoming DraftKings markets; retaining existing files")
        return
    print(f"DK game odds: {len(rows)} eligible provider events")
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
        print(f"DK game odds: {len(rows)} provider events, zero matched published games; retaining existing files")
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
