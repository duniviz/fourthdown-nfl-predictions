"""Read-only consistency audit for FOURTHDOWN current player and game feeds.

Separate game, yardage and count models are intentional. The audit verifies
that their published outputs refer to the same season/week, and simulations
refer to the same exact game IDs. It never changes projections or odds.
"""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))

game = load("live-v2.json")
player = load("player-research.json")
counts = load("count-projections.json")
sim = load("simulations.json")
season, week = int(game["season"]), int(game["week"])
assert game.get("games"), "No current game projections"
for name, feed in (("player-research.json", player), ("count-projections.json", counts)):
    assert (int(feed["season"]), int(feed["week"])) == (season, week), (
        f"{name} targets {feed.get('season')}/{feed.get('week')} "
        f"but game projections target {season}/{week}"
    )
    assert feed.get("players"), f"{name} has no player projections"

game_ids = {g["game_id"] for g in game["games"]}
assert len(game_ids) == len(game["games"]), "Duplicate game IDs in score projections"
sim_ids = {g["game_id"] for g in sim.get("games", [])}
assert sim_ids == game_ids, f"Simulation games differ from score projections: {sim_ids ^ game_ids}"
assert all(p.get("game_id") in game_ids for p in sim.get("players", [])), (
    "Simulation players contain a game outside current score projections"
)
assert all(p.get("game_id") in game_ids for p in player["players"]), (
    "Player yardage forecasts contain a game outside current score projections"
)
print(f"PASS: season {season} week {week}; {len(game_ids)} games; "
      f"{len(player['players'])} player research rows; "
      f"{len(counts['players'])} count-prop rows; "
      f"{len(sim.get('players', []))} simulated player markets")
