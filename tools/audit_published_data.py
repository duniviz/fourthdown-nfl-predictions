#!/usr/bin/env python3
"""Read-only integrity checks for FOURTHDOWN published feeds."""
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data"
now = dt.datetime.now(dt.timezone.utc)
warnings = []
errors = []

def load(name):
    path = ROOT / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"{name}: unreadable JSON ({type(exc).__name__})")
        return {}

def age(label, stamp, max_hours=36):
    if not stamp:
        warnings.append(f"{label}: no timestamp")
        return
    try:
        when = dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
        if when.tzinfo is None:
            when = when.replace(tzinfo=dt.timezone.utc)
        hours = (now - when).total_seconds() / 3600
        if hours > max_hours:
            warnings.append(f"{label}: stale by {hours:.1f} hours")
        elif hours < -1:
            warnings.append(f"{label}: timestamp is in the future")
    except ValueError:
        errors.append(f"{label}: invalid timestamp {stamp}")

games = load("dk-game-odds.json")
rows = games.get("games", [])
if not rows:
    warnings.append("game odds: no games")
for game in rows:
    age(f"game odds {game.get('game_id','unknown')}", game.get("updated_at_utc") or games.get("snapshot_date_utc"), 48)
    if game.get("home_spread") is not None and abs(game["home_spread"]) > 35:
        warnings.append(f"game odds {game.get('game_id')}: extreme spread")
    if game.get("total") is not None and not 15 <= game["total"] <= 90:
        warnings.append(f"game odds {game.get('game_id')}: extreme total")

props = load("dk-odds.json")
age("player odds", props.get("generated_at_utc"))
if not props.get("rows"):
    warnings.append("player odds: no rows")
for row in props.get("rows", []):
    line = row.get("line")
    if isinstance(line, (int, float)) and (line < 0 or line > 650):
        warnings.append(f"player odds {row.get('player')}: unusual line {line}")

injuries = load("injuries.json")
teams = injuries.get("teams", {})
if teams and all(not t.get("players") for t in teams.values()):
    warnings.append("injuries: all team player lists are empty; verify feed/parser")
if injuries.get("model_adjusted") is False:
    warnings.append("injuries: not incorporated into model adjustments")

results = load("player-results.json")
graded = results.get("rows", [])
if graded and all(row.get("dk_line") is None for row in graded):
    warnings.append("player results: no historical DraftKings lines; cannot grade edge")
for row in graded:
    if isinstance(row.get("error"), (int, float)) and abs(row["error"]) >= 75:
        warnings.append(f"projection outlier: {row.get('player')} {row.get('market')} error={row['error']}")

print(f"FOURTHDOWN data audit: {len(errors)} errors, {len(warnings)} warnings")
for item in errors:
    print("ERROR:", item)
for item in warnings:
    print("WARNING:", item)
if errors:
    raise SystemExit(1)
