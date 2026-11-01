"""Fetch DraftKings NFL lines server-side; never expose the API key in public assets."""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from collections import defaultdict
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
    # Persist the latest observed pre-kickoff quote for each exact matchup,
    # player and market. Never replace a locked line with an in-game price.
    archive_path = Path("data/dk-pregame-lines.json")
    try:
        old = json.loads(archive_path.read_text(encoding="utf-8")) if archive_path.exists() else {}
        saved = old.get("rows", []) if isinstance(old, dict) else []
    except (ValueError, OSError):
        saved = []
    by_key = {}
    def key_for(row):
        return tuple(str(row.get(k) or "").strip().lower() for k in (
            "commence_time", "home_team", "away_team", "player", "market_key"
        ))
    for row in saved:
        if isinstance(row, dict) and all(key_for(row)):
            by_key[key_for(row)] = row
    now = datetime.now(timezone.utc)
    for row in cleaned:
        k = key_for(row)
        if not all(k) or row.get("line") is None:
            continue
        try:
            kickoff = datetime.fromisoformat(str(row["commence_time"]).replace("Z", "+00:00"))
            updated = datetime.fromisoformat(str(row["last_update"]).replace("Z", "+00:00"))
            if kickoff.tzinfo is None or updated.tzinfo is None:
                continue
            if now >= kickoff or updated > kickoff or updated > now:
                continue
            float(row["line"])
        except (ValueError, TypeError, KeyError):
            continue
        previous = by_key.get(k)
        if previous:
            try:
                old_time = datetime.fromisoformat(str(previous["last_update"]).replace("Z", "+00:00"))
                if updated <= old_time:
                    continue
            except (ValueError, TypeError):
                pass
        by_key[k] = {**row, "saved_at_utc": now.isoformat()}
    archive_path.parent.mkdir(exist_ok=True)
    archive_path.write_text(json.dumps({
        "source": "DraftKings via ParlayAPI",
        "description": "Latest observed quote strictly before scheduled kickoff, not necessarily closing line",
        "generated_at_utc": now.isoformat(),
        "rows": sorted(by_key.values(), key=lambda x: (str(x.get("commence_time")), str(x.get("player")), str(x.get("market_key"))))
    }, indent=2) + "\\n", encoding="utf-8")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "ParlayAPI", "bookmaker": "draftkings", "rows": cleaned
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Published {len(cleaned)} DraftKings NFL prop rows")

if __name__ == "__main__":
    fetch()
