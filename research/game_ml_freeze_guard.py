"""Early independent game ML freeze window; never delay official DraftKings capture."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from live.game_pregame_observations import dt

def due(games, now):
    for game in games:
        kickoff = dt(game.get("kickoff_utc"))
        if kickoff and timedelta(minutes=45) <= kickoff - now <= timedelta(minutes=90):
            return True
    return False

def main():
    path = Path("data/live-v2.json")
    games = json.loads(path.read_text()).get("games", []) if path.exists() else []
    eligible = due(games, datetime.now(timezone.utc))
    print("Independent early game ML freeze:", "due" if eligible else "not due")
    if not eligible:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
