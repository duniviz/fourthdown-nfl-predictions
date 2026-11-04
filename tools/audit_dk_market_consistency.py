"""Validate published DraftKings game quotes against their pregame history."""
import datetime as dt
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))
odds = load("dk-game-odds.json")
history = load("dk-game-line-history.json").get("games", {})
errors = []
seen = set()
for row in odds.get("games", []):
    home, away, kickoff = (row.get(k) for k in ("home", "away", "commence_time"))
    key = f"{home}|{away}|{kickoff}"
    if not home or not away or not kickoff:
        errors.append(f"Incomplete game identity: {row.get('game_id')}")
        continue
    if key in seen:
        errors.append(f"Duplicate DK game: {key}")
    seen.add(key)
    if home == away:
        errors.append(f"Same home and away team: {key}")
    spread, total = row.get("home_spread"), row.get("total")
    if spread is None and total is None:
        errors.append(f"Game without spread or total: {key}")
    for label, value, low, high in (("spread", spread, -35, 35), ("total", total, 15, 100)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, (float, int)) or not low <= value <= high):
            errors.append(f"Invalid {label} for {key}: {value}")
    if key not in history:
        errors.append(f"No saved pregame quote history: {key}")
    try:
        dt.datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        errors.append(f"Invalid kickoff timestamp: {key}")
if errors:
    raise SystemExit("\\n".join(errors))
print(f"PASS: {len(seen)} unique DraftKings games, numeric market sanity and quote-history linkage")
