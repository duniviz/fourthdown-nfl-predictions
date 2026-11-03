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
        opponent = {"LA": "LAR", "WSH": "WAS", "JAX": "JAC"}.get(raw_opponent, raw_opponent)
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
if players_path.exists():
    raw = players_path.read_text().strip()
    if not raw:
        print("BLOCKER: player-research.json is empty; live player-card explanations cannot render")
    else:
        players = json.loads(raw).get("players", [])
        if not players:
            print("BLOCKER: player-research.json has no players")
        else:
            print(f"Player research feed contains {len(players)} records")
