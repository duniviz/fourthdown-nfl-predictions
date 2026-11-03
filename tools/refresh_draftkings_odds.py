#!/usr/bin/env python3
"""Fetch licensed DraftKings NFL odds via The Odds API. Requires ODDS_API_KEY."""
import datetime as dt
import json
import os
import pathlib
import urllib.parse
import urllib.request

BASE = "https://api.the-odds-api.com/v4"
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "draftkings_odds.json"
KEY = os.environ.get("ODDS_API_KEY")
GAME_MARKETS = "h2h,spreads,totals"
PROP_MARKETS = "player_pass_yds,player_rush_yds,player_reception_yds,player_receptions,player_pass_tds,player_anytime_td"
MAX_EVENTS = int(os.environ.get("MAX_PROP_EVENTS", "16"))

def fetch(path, **params):
    params["apiKey"] = KEY
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "FOURTHDOWN/1.0"}), timeout=35) as response:
        return json.load(response)

def dk_markets(event):
    books = [b for b in event.get("bookmakers", []) if b.get("key") == "draftkings"]
    return [{"key": m["key"], "last_update": m.get("last_update"), "outcomes": m.get("outcomes", [])}
            for b in books for m in b.get("markets", [])]

def main():
    if not KEY:
        raise SystemExit("ODDS_API_KEY secret is required; refusing to publish empty or invented odds")
    now = dt.datetime.now(dt.timezone.utc)
    games = fetch("/sports/americanfootball_nfl/odds", regions="us", markets=GAME_MARKETS,
                  bookmakers="draftkings", oddsFormat="american", dateFormat="iso")
    result = {"source": "The Odds API", "bookmaker": "draftkings", "fetched_at": now.isoformat(),
              "timezone": "UTC", "games": [], "player_props": [], "warnings": []}
    upcoming = []
    for event in games:
        game = {k: event.get(k) for k in ("id", "sport_key", "commence_time", "home_team", "away_team")}
        game["markets"] = dk_markets(event)
        result["games"].append(game)
        if game["markets"] and event.get("commence_time", "") >= now.isoformat().replace("+00:00", "Z"):
            upcoming.append(event)
    for event in upcoming[:MAX_EVENTS]:
        try:
            data = fetch("/sports/americanfootball_nfl/events/" + urllib.parse.quote(event["id"]) + "/odds",
                         regions="us", markets=PROP_MARKETS, bookmakers="draftkings",
                         oddsFormat="american", dateFormat="iso")
            result["player_props"].append({"event_id": event["id"], "home_team": event.get("home_team"),
                "away_team": event.get("away_team"), "markets": dk_markets(data)})
        except Exception as exc:
            result["warnings"].append({"event_id": event["id"], "error": type(exc).__name__})
    if not result["games"]:
        result["warnings"].append({"message": "No NFL DraftKings game markets returned"})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    tmp.replace(OUT)
    # Publish the existing dashboard schemas as well, without changing predictions.
    import re
    abbreviations = {"Arizona Cardinals":"ARI","Atlanta Falcons":"ATL","Baltimore Ravens":"BAL","Buffalo Bills":"BUF","Carolina Panthers":"CAR","Chicago Bears":"CHI","Cincinnati Bengals":"CIN","Cleveland Browns":"CLE","Dallas Cowboys":"DAL","Denver Broncos":"DEN","Detroit Lions":"DET","Green Bay Packers":"GB","Houston Texans":"HOU","Indianapolis Colts":"IND","Jacksonville Jaguars":"JAX","Kansas City Chiefs":"KC","Las Vegas Raiders":"LV","Los Angeles Chargers":"LAC","Los Angeles Rams":"LA","Miami Dolphins":"MIA","Minnesota Vikings":"MIN","New England Patriots":"NE","New Orleans Saints":"NO","New York Giants":"NYG","New York Jets":"NYJ","Philadelphia Eagles":"PHI","Pittsburgh Steelers":"PIT","San Francisco 49ers":"SF","Seattle Seahawks":"SEA","Tampa Bay Buccaneers":"TB","Tennessee Titans":"TEN","Washington Commanders":"WAS"}
    def write_json(name, payload):
        target = ROOT / "data" / name
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temp.replace(target)
    game_rows = []
    for game in result["games"]:
        home, away = abbreviations.get(game["home_team"]), abbreviations.get(game["away_team"])
        if not home or not away: continue
        kickoff = dt.datetime.fromisoformat(game["commence_time"].replace("Z","+00:00"))
        # ESPN week identifiers can vary; match by teams and kickoff on the client.
        spread = next((m for m in game["markets"] if m["key"]=="spreads"), None)
        total = next((m for m in game["markets"] if m["key"]=="totals"), None)
        h2h = next((m for m in game["markets"] if m["key"]=="h2h"), None)
        home_spread = next((o.get("point") for o in spread["outcomes"] if o["name"]==game["home_team"]), None) if spread else None
        total_points = next((o.get("point") for o in total["outcomes"] if o["name"]=="Over"), None) if total else None
        if home_spread is None and total_points is None: continue
        game_rows.append({"game_id":game["id"],"home":home,"away":away,"home_team":game["home_team"],"away_team":game["away_team"],"commence_time":game["commence_time"],"bookmaker":"draftkings","home_spread":home_spread,"total":total_points,"moneyline":h2h["outcomes"] if h2h else [],"updated_at_utc":result["fetched_at"]})
    # Never erase existing lines if the provider returned no valid games.
    if game_rows:
        write_json("dk-game-odds.json", {"source":"The Odds API","bookmaker":"draftkings","snapshot_date_utc":now.date().isoformat(),"games":game_rows})
    prop_rows = []
    for event in result["player_props"]:
        for market in event["markets"]:
            grouped = {}
            for outcome in market["outcomes"]:
                player = outcome.get("description") or outcome.get("name")
                if not player: continue
                row = grouped.setdefault(player, {"player":player,"market_key":market["key"],"line":outcome.get("point"),"over_price":None,"under_price":None,"yes_price":None,"no_price":None,"home_team":event["home_team"],"away_team":event["away_team"],"last_update":market.get("last_update")})
                side = outcome.get("name","").lower()
                if side in ("over","under","yes","no"): row[side+"_price"] = outcome.get("price")
            prop_rows.extend(x for x in grouped.values() if x["line"] is not None or x["market_key"]=="player_anytime_td")
    if prop_rows:
        write_json("dk-odds.json", {"generated_at_utc":result["fetched_at"],"source":"The Odds API","bookmaker":"draftkings","rows":prop_rows})
    print(f"Published {len(result['games'])} games and {len(result['player_props'])} event prop sets")

if __name__ == "__main__":
    main()
