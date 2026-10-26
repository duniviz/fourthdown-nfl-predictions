"""Run rolling historical evaluation from downloaded CSV files."""
import json
from pathlib import Path
from .rolling import load_rows, build_rolling_predictions, summarize

def main():
    folder = Path("data")
    games = build_rolling_predictions(load_rows(folder / "schedules.csv"), load_rows(folder / "team_epa.csv"))
    result = summarize(games)
    result["by_season"] = {str(year): summarize([r for r in games if r["season"] == year]) for year in sorted({r["season"] for r in games})}
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
