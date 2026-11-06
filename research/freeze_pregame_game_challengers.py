"""Freeze game ML challengers from the latest public schedule at the pregame refresh.

No results or odds are used as model features. Forecasts are written only
before kickoff by scripts/freeze_game_ml_predictions.py.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

def main():
    import nflreadpy
    schedule = nflreadpy.load_schedules(list(range(2016, 2027)))
    if not len(schedule):
        raise SystemExit("No NFL schedule rows available for challenger freeze")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "schedule.csv"
        schedule.write_csv(path)
        subprocess.run([sys.executable, "scripts/freeze_game_ml_predictions.py", str(path)], check=True)
    archive = Path("data/weekly-shadow-forecasts.json")
    rows = json.loads(archive.read_text()).get("rows", [])
    print("Frozen game challenger forecasts:", sum(
        r.get("player_id") == "GAME" and str(r.get("model", "")).startswith("ml_")
        for r in rows
    ))

if __name__ == "__main__":
    main()
