"""Run model with a JSON file of explicit pregame inputs.

Usage: python -m model.run examples/sample_game.json
"""
import json
import sys
from pathlib import Path
from .engine import GameInput, TeamRating, simulate

def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m model.run PATH_TO_INPUT.json")
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    game = GameInput(
        away=TeamRating(**data["away"]), home=TeamRating(**data["home"]),
        **data.get("game_settings", {}))
    result = simulate(game, **data.get("simulation_settings", {}))
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
