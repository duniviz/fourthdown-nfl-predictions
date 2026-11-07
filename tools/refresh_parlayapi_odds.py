#!/usr/bin/env python3
"""Refresh DraftKings NFL game lines and player props using ParlayAPI."""
import datetime as dt
import json
import os
import sys
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

def merge_player_quotes(previous, incoming, now):
    """Keep distinct upcoming DK markets and preserve the newest observed quote.

    Milestone/threshold markets offer several lines per player; ordinary full-game
    O/U markets offer one line that can move. Never treat these as equivalent.
    """
    def identity(row):
        fields = ("player", "market_key", "home_team", "away_team", "commence_time")
        key = tuple(str(row.get(field) or "").strip().lower() for field in fields)
        market = key[1]
        if "milestone" in market or "to_record_x+" in market:
            key += (str(row.get("line")),)
        return key

    def parsed_time(value):
        try:
            result = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return result if result.tzinfo else None
        except (TypeError, ValueError):
            return None

    def usable(row):
        if not isinstance(row, dict):
            return False
        if str(row.get("market_key", "")).lower().endswith("_spread"):
            return False
        try:
            line = float(row["line"])
        except (KeyError, TypeError, ValueError):
            return False
        if not (-float("inf") < line < float("inf")):
            return False
        kickoff = parsed_time(row.get("commence_time"))
        updated = parsed_time(row.get("last_update"))
        return bool(kickoff and updated and now < kickoff and updated <= now
                    and updated < kickoff and all(identity(row)[:5]))

    merged = {}
    for row in list(previous) + list(incoming):
        if not usable(row):
            continue
        key = identity(row)
        old = merged.get(key)
        if old is None or parsed_time(row["last_update"]) > parsed_time(old["last_update"]):
            merged[key] = row
    return list(merged.values())

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

def capture_game_history(game_rows, now):
    """Append observed line changes without spending additional API calls."""
    history = load("dk-game-line-history.json", {"schema_version": 1, "games": {}})
    games = history.setdefault("games", {})
    for row in game_rows:
        key = opening_key(row, ("home", "away", "commence_time"))
        if not key:
            continue
        entries = games.setdefault(key, [])
        quote = {"captured_at_utc": now, "home_spread": row.get("home_spread"), "total": row.get("total")}
        if not entries or any(entries[-1].get(k) != quote[k] for k in ("home_spread", "total")):
            entries.append(quote)
        # Bound repository growth while retaining the initial observation.
        if len(entries) > 100:
            games[key] = [entries[0]] + entries[-99:]
    history["schema_version"] = 1
    history["updated_at_utc"] = now
    return history

def main():
    if not KEY:
        raise SystemExit("PARLAY_API_KEY GitHub Actions secret required")
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    # The official T-15 game capture owns game odds. Avoid a second paid game request.
    props_only = "--props-only" in sys.argv
    events = [] if props_only else request("/odds", regions="us", markets="h2h,spreads,totals", bookmakers="draftkings", oddsFormat="american", dateFormat="iso")
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
        # Player spread/handicap markets are not standard over/under totals.
        # In particular, negative spread values must not appear as yardage lines.
        if str(p.get("market_key", "")).lower().endswith("_spread"):
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
    # Diagnose missing player quotes from this already-paid provider response.
    # No additional API calls, no made-up lines, and no player-specific overrides.
    from collections import Counter
    passing = [row for row in prop_rows if "passing_yards" in str(row.get("market_key", "")).lower()]
    print(f"DK coverage: {len(passing)} passing-yards quote rows, {len(set(str(r.get('player','')).casefold() for r in passing))} unique players")
    for expected in ("Michael Penix", "Joe Burrow"):
        matched = [r for r in prop_rows if expected.casefold() in str(r.get("player", "")).casefold()]
        print(f"DK coverage {expected}: {len(matched)} provider quote(s); market keys: {dict(Counter(str(r.get('market_key')) for r in matched))}")
    # If a player is absent here, the quote was not in the returned DK provider payload.
    # If present but absent on the site, inspect downstream identity/market matching.
    # Never overwrite valid published snapshots with an empty or partial provider response.
    # Publish each market family independently. A missing game market must not
    # prevent valid player quotes from updating (or vice versa).
    if game_rows:
        save("dk-game-odds.json", {"source":"ParlayAPI","bookmaker":"draftkings","snapshot_date_utc":now,"games":game_rows})
        save("dk-game-line-history.json", capture_game_history(game_rows, now))
    elif not props_only:
        print("WARNING: No DraftKings spreads/totals from provider; retaining last verified game snapshot")
    if prop_rows:
        previous = load("dk-odds.json", {}).get("rows", [])
        retained = merge_player_quotes(previous, prop_rows, dt.datetime.now(dt.timezone.utc))
        save("dk-odds.json", {"generated_at_utc":now,"source":"ParlayAPI","bookmaker":"draftkings","rows":retained})
        print(f"Published {len(retained)} distinct upcoming-market quotes from {len(prop_rows)} provider rows; "
              f"retained {sum(1 for row in retained if row not in prop_rows)} previously saved quotes")
    else:
        print("WARNING: No DraftKings player quotes from provider; retaining last verified prop snapshot")
    if game_rows or prop_rows:
        save("dk-opening-odds.json", capture_openings(game_rows, prop_rows, now))
    else:
        raise SystemExit("No DraftKings game or player markets returned; preserving prior data")
    print(f"ParlayAPI refreshed {len(game_rows)} games, {len(prop_rows)} player quotes")

if __name__ == "__main__":
    main()
