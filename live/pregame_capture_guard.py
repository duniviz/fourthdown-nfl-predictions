"""Gate lightweight pregame capture near scheduled kickoffs (no API calls)."""
import json
from datetime import datetime, timezone
from pathlib import Path
from live.game_pregame_observations import dt

def due(games, now):
    for game in games:
        kickoff=dt(game.get("kickoff_utc"))
        if kickoff and -45 <= (kickoff-now).total_seconds()/60 <= 150:
            return True
    return False

def main():
    path=Path("data/live-v2.json")
    games=json.loads(path.read_text()).get("games",[]) if path.exists() else []
    now=datetime.now(timezone.utc)
    if due(games,now):
        print("Upcoming/recent NFL kickoff: capture enabled")
        return
    print("No kickoff near capture window")
    raise SystemExit(1)

if __name__=="__main__":
    main()
