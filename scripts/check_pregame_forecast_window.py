"""Allow a full forecast refresh 45–115 minutes before a published kickoff."""
import json
from datetime import datetime,timezone
from pathlib import Path
from live.game_pregame_observations import dt
def due(games,now):
    return any(k is not None and 45 <= (k-now).total_seconds()/60 <= 115 for g in games for k in [dt(g.get("kickoff_utc"))])
def main():
    p=Path("data/live-v2.json")
    games=json.loads(p.read_text()).get("games",[]) if p.exists() else []
    if due(games,datetime.now(timezone.utc)):
        print("Pregame forecast refresh due")
        return
    print("No kickoff 45–115 minutes away")
    raise SystemExit(1)
if __name__=="__main__":
    main()
