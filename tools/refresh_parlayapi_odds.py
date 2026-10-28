#!/usr/bin/env python3
"""Refresh DraftKings NFL game lines and player props using ParlayAPI."""
import datetime as dt
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1] / "data"
BASE = "https://parlay-api.com/v1/sports/americanfootball_nfl"
KEY = os.environ.get("PARLAY_API_KEY")
TEAMS = dict(zip(
    "ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LV LAC LA MIA MIN NE NO NYG NYJ PHI PIT SF SEA TB TEN WAS".split(),
    ["Arizona Cardinals","Atlanta Falcons","Baltimore Ravens","Buffalo Bills","Carolina Panthers","Chicago Bears","Cincinnati Bengals","Cleveland Browns","Dallas Cowboys","Denver Broncos","Detroit Lions","Green Bay Packers","Houston Texans","Indianapolis Colts","Jacksonville Jaguars","Kansas City Chiefs","Las Vegas Raiders","Los Angeles Chargers","Los Angeles Rams","Miami Dolphins","Minnesota Vikings","New England Patriots","New Orleans Saints","New York Giants","New York Jets","Philadelphia Eagles","Pittsburgh Steelers","San Francisco 49ers","Seattle Seahawks","Tampa Bay Buccaneers","Tennessee Titans","Washington Commanders"]
))
ABBR = {v:k for k,v in TEAMS.items()}

def request(endpoint, **params):
    url = BASE + endpoint + "?" + urlencode(params)
    with urlopen(Request(url, headers={"X-API-Key": KEY, "User-Agent":"FOURTHDOWN/1.0"}), timeout=45) as response:
        data = json.load(response)
    if not isinstance(data, list):
        raise ValueError("Unexpected ParlayAPI response shape for " + endpoint)
    return data

def timestamp(value):
    if isinstance(value, (float, int)):
        return dt.datetime.fromtimestamp(value / (1000 if value > 1e11 else 1), dt.timezone.utc).isoformat()
    return value

def save(filename, payload):
    ROOT.mkdir(exist_ok=True, parents=True)
    target = ROOT / filename
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)

def load(filename, fallback):
    target = ROOT / filename
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else fallback
    except (OSError, json.JSONDecodeError):
        return fallback

def opening_key(row, fields):
    return "|".join(str(row.get(field) or "") for field in fields)

def capture_openings(game_rows, prop_rows, now):
    """Keep the first valid DraftKings quote observed for every market."""
    opening = load("dk-opening-odds.json", {"schema_version": 1, "source": "ParlayAPI", "bookmaker": "draftkings", "games": {}, "props": {}})
    games = opening.setdefault("games", {})
    props = opening.setdefault("props", {})
    for row in game_rows:
        key = opening_key(row, ("home", "away", "commence_time"))
        if key and key not in games:
            games[key] = {**row, "opening_captured_at_utc": now}
    for row in prop_rows:
        key = opening_key(row, ("player", "market_key", "home_team", "away_team", "commence_time"))
        if key and key not in props:
            props[key] = {**row, "opening_captured_at_utc": now}
    opening["schema_version"] = 1
    opening["source"] = "ParlayAPI"
    opening["bookmaker"] = "draftkings"
    opening["updated_at_utc"] = now
    return opening

def main():
    if not KEY:
        raise SystemExit("PARLAY_API_KEY GitHub Actions secret required")
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    events = request("/odds", regions="us", markets="h2h,spreads,totals", bookmakers="draftkings", oddsFormat="american", dateFormat="iso")
    props = request("/props", bookmakers="draftkings", limit=10000)
    game_rows = []
    for e in events:
        home, away = e.get("home_team"), e.get("away_team")
        if home not in ABBR or away not in ABBR:
            continue
        books = [b for b in e.get("bookmakers", []) if b.get("key") == "draftkings"]
        markets = {m.get("key"):m for b in books for m in b.get("markets", [])}
        def outcome(market, name, field):
            return next((o.get(field) for o in markets.get(market, {}).get("outcomes", []) if o.get("name") == name), None)
        spread = outcome("spreads", home, "point")
        total = outcome("totals", "Over", "point")
        if spread is None and total is None:
            continue
        game_rows.append({"game_id":e.get("id"),"home":ABBR[home],"away":ABBR[away],"home_team":home,"away_team":away,"commence_time":e.get("commence_time"),"bookmaker":"draftkings","home_spread":spread,"total":total,"moneyline":markets.get("h2h", {}).get("outcomes", []),"updated_at_utc":now})
    prop_rows = []
    for p in props:
        if p.get("bookmaker") != "draftkings" or not p.get("player") or not p.get("market_key"):
            continue
        line = p.get("line")
        if line is None:
            continue
        try:
            float(line)
        except (TypeError, ValueError):
            continue
        row = {k:p.get(k) for k in ("player","market_key","line","over_price","under_price","yes_price","no_price","home_team","away_team","commence_time","age_seconds")}
        row["last_update"] = timestamp(p.get("last_update"))
        prop_rows.append(row)
    # Never overwrite valid published snapshots with an empty or partial provider response.
    if not game_rows:
        raise SystemExit("No DraftKings game spreads/totals returned; preserving prior data")
    if not prop_rows:
        raise SystemExit("No DraftKings player props returned; preserving prior data")
    save("dk-game-odds.json", {"source":"ParlayAPI","bookmaker":"draftkings","snapshot_date_utc":now,"games":game_rows})
    save("dk-odds.json", {"generated_at_utc":now,"source":"ParlayAPI","bookmaker":"draftkings","rows":prop_rows})
    save("dk-opening-odds.json", capture_openings(game_rows, prop_rows, now))
    print(f"ParlayAPI refreshed {len(game_rows)} games, {len(prop_rows)} player quotes")

if __name__ == "__main__":
    main()
