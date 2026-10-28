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
    print(f"Published {len(result['games'])} games and {len(result['player_props'])} event prop sets")

if __name__ == "__main__":
    main()
