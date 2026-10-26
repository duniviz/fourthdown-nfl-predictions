"""Print head-to-head v1/v2 comparisons on exactly matched games."""
import json
from pathlib import Path
from .rolling import load_rows, build_rolling_predictions, summarize
from .v2 import build_v2_predictions

def compare(schedules, team_games):
    baseline = build_rolling_predictions(schedules, team_games)
    candidate = build_v2_predictions(schedules, team_games)
    base_map = {r["game_id"]: r for r in baseline}
    v2_map = {r["game_id"]: r for r in candidate}
    common = sorted(base_map.keys() & v2_map.keys())
    def metrics(keys, model):
        return summarize([model[k] for k in keys])
    result = {
        "matched_games": len(common),
        "development_2021_2024": {
            "v1": metrics([k for k in common if int(base_map[k]["season"]) <= 2024], base_map),
            "v2": metrics([k for k in common if int(base_map[k]["season"]) <= 2024], v2_map)
        },
        "held_out_2025": {
            "v1": metrics([k for k in common if int(base_map[k]["season"]) == 2025], base_map),
            "v2": metrics([k for k in common if int(base_map[k]["season"]) == 2025], v2_map)
        },
        "by_season": {
            str(y): {
                "v1": metrics([k for k in common if int(base_map[k]["season"]) == y], base_map),
                "v2": metrics([k for k in common if int(base_map[k]["season"]) == y], v2_map)
            }
            for y in sorted({int(base_map[k]["season"]) for k in common})
        },
        "warning": "Candidate coefficients are hypotheses, not calibrated; no 2025 tuning permitted."
    }
    return result

def main():
    folder = Path("data")
    result = compare(load_rows(folder / "schedules.csv"),
                     load_rows(folder / "team_epa.csv"))
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
