"""Fetch DraftKings NFL lines server-side; never expose the API key in public assets."""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://parlay-api.com/v1/sports/americanfootball_nfl"
# Request only markets the provider labels explicitly.  The client matches a
# projection to this canonical key; it never guesses that a similarly named
# book market is equivalent.
MARKETS = ",".join((
    "player_pass_yds", "player_pass_attempts", "player_pass_completions",
    "player_pass_tds", "player_pass_interceptions", "player_rush_yds",
    "player_rush_attempts", "player_rec_yds", "player_receptions",
    "player_rush_tds", "player_rec_tds", "player_anytime_td",
))
OUT = Path("data/dk-odds.json")

def fetch():
    key = os.environ.get("PARLAY_API_KEY", "").strip()
    if not key:
        print("PARLAY_API_KEY missing; leaving existing lines untouched")
        return
    url = BASE + "/props?" + urllib.parse.urlencode({
        "bookmakers": "draftkings", "markets": MARKETS, "limit": 1000
    })
    request = urllib.request.Request(url, headers={"X-API-Key": key, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = next((payload[k] for k in ("data", "props", "results") if isinstance(payload.get(k), list)), [])
    else:
        raise ValueError("Unexpected ParlayAPI response")
    cleaned = []
    for row in rows:
        if not isinstance(row, dict) or str(row.get("bookmaker", "")).lower() != "draftkings":
            continue
        if not row.get("player") or not row.get("market_key"):
            continue
        cleaned.append({k: row.get(k) for k in (
            "player", "market_key", "line", "over_price", "under_price",
            "yes_price", "no_price",
            "home_team", "away_team", "commence_time", "last_update", "age_seconds"
        )})
    # Do not overwrite a previously useful snapshot with an empty/unknown response.
    if not cleaned:
        print("No DraftKings NFL props in current API response; leaving snapshot unchanged")
        return
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "ParlayAPI", "bookmaker": "draftkings", "rows": cleaned
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Published {len(cleaned)} DraftKings NFL prop rows")

if __name__ == "__main__":
    fetch()
