#!/usr/bin/env python3
"""Recover missing pregame DK player markets from a verified older snapshot.

No provider calls. Preserve current quotes and original historical timestamps.
"""
import datetime as dt
import json
import subprocess
from pathlib import Path

HISTORICAL_COMMIT = "9b536691d"
FILE = "data/dk-odds.json"
ALIASES = {
    "player_pass_yds": "player_passing_yards",
    "player_rush_yds": "player_rushing_yards",
    "player_rec_yds": "player_receiving_yards",
}
def parse(value):
    try:
        result = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result if result.tzinfo else None
    except (ValueError, TypeError):
        return None

def recover(current, historical, now):
    rows = current["rows"]
    def identity(row):
        return tuple(str(row.get(k, "")).strip().lower() for k in
                     ("player", "market_key", "home_team", "away_team", "commence_time"))
    def canonical(row):
        key = list(identity(row))
        key[1] = ALIASES.get(key[1], key[1])
        kickoff = parse(row.get("commence_time"))
        # Same game can be encoded with different ISO timestamp precision.
        key[4] = kickoff.isoformat() if kickoff else key[4]
        return tuple(key)
    latest = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = canonical(row)
        updated = parse(row.get("last_update"))
        if key not in latest or (updated and (not latest[key] or updated > latest[key])):
            latest[key] = updated
    restored = []
    for row in historical.get("rows", []):
        if not isinstance(row, dict) or row.get("market_key") not in ALIASES:
            continue
        kickoff, updated = parse(row.get("commence_time")), parse(row.get("last_update"))
        if not kickoff or not updated or kickoff <= now or updated > now or updated >= kickoff:
            continue
        if not all(identity(row)):
            continue
        try:
            float(row["line"])
        except (KeyError, ValueError, TypeError):
            continue
        key = canonical(row)
        # Do not replace any current standard quote, even if its key uses the new alias.
        if key in latest:
            continue
        restored.append(row)
        rows.append(row)
        latest[key] = updated
    return restored

def main():
    current = json.loads(Path(FILE).read_text(encoding="utf-8"))
    historical = json.loads(subprocess.check_output(
        ["git", "show", f"{HISTORICAL_COMMIT}:{FILE}"], text=True))
    restored = recover(current, historical, dt.datetime.now(dt.timezone.utc))
    if restored:
        Path(FILE).write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    print(f"Recovered {len(restored)} missing historical player markets without API calls")
    for row in restored:
        if row["player"] in ("Samaje Perine", "Kyle Pitts", "Chase Brown"):
            print(f'{row["player"]}: {row["market_key"]} {row["line"]} '
                  f'(historical {row["last_update"]})')

if __name__ == "__main__":
    main()
