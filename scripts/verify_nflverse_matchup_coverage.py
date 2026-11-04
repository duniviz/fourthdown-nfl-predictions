"""Validate nflverse matchup coverage against game IDs without modifying projections."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
matchups = json.loads((root / "data/nflverse-defensive-matchups.json").read_text())
games = json.loads((root / "data/live-v2.json").read_text())["games"]
contexts = matchups["contexts"]
assert matchups["source"] == "nflverse"
assert len(contexts) > 100, "Matchup data missing"
checked = 0
for game in games:
    season, week, *_ = game["game_id"].split("_")
    for raw_opponent in (game["home"], game["away"]):
        opponent = {"LA": "LAR", "WSH": "WAS", "JAC": "JAX"}.get(raw_opponent, raw_opponent)
        for position, market in (
            ("QB", "passing_yards"),
            ("RB", "rushing_yards"),
            ("WR", "receiving_yards"),
            ("TE", "receiving_yards"),
        ):
            key = f"{season}|{int(week)}|{opponent}|{position}|{market}"
            if key not in contexts:
                raise AssertionError(f"Missing matchup context for {game['game_id']}: {key}")
            item = contexts[key]
            assert 1 <= item["rank"] <= item["ranked_teams"] <= 32, key
            assert item["games"] >= 3, key
            assert item["last_5_games"] <= 5, key
            checked += 1
print(f"Verified {checked} game/opponent/position contexts")
players_path = root / "data/player-research.json"
assert players_path.exists() and players_path.stat().st_size > 0, "Production player feed is missing or empty"
feed = json.loads(players_path.read_text(encoding="utf-8"))
players = feed.get("players")
assert isinstance(players, list) and players, "Production player feed has no players"
checked_players = 0
missing = []
aliases = {"LA": "LAR", "WSH": "WAS", "JAC": "JAX"}
for player in players:
    position = str(player.get("position", "")).upper()
    market = player.get("stat_key")
    if (position, market) not in {("QB", "passing_yards"), ("RB", "rushing_yards"),
                                   ("WR", "receiving_yards"), ("TE", "receiving_yards")}:
        continue
    game_id = str(player.get("game_id", ""))
    parts = game_id.split("_")
    assert len(parts) >= 3, f"Invalid player game_id: {game_id}"
    opponent = aliases.get(player.get("opponent"), player.get("opponent"))
    key = f"{parts[0]}|{int(parts[1])}|{opponent}|{position}|{market}"
    if key not in contexts:
        missing.append(key)
    checked_players += 1
assert checked_players, "No supported player yardage records in production feed"
assert not missing, f"Missing {len(missing)} player matchup contexts; examples: {missing[:8]}"
print(f"Verified {checked_players} player yardage records with correct opponent/week/position contexts")
