"""Allow a full forecast refresh 80–150 minutes before a published kickoff."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from live.game_pregame_observations import dt

MIN_MINUTES = 80
MAX_MINUTES = 150
FRESH_MINUTES = 45
FORECAST_FRESH = timedelta(hours=2)


def recently_refreshed(data, now):
    generated = dt(data.get("generated_at_utc"))
    if generated is None:
        return False
    age = (now - generated).total_seconds() / 60
    return 0 <= age < FRESH_MINUTES


def due(games, now):
    return any(
        kickoff is not None
        and MIN_MINUTES <= (kickoff - now).total_seconds() / 60 <= MAX_MINUTES
        for game in games
        for kickoff in [dt(game.get("kickoff_utc"))]
    )


def due_games_covered(games, generated, now):
    """True when every kickoff already inside the 80–150 minute window has a 2-hour-fresh forecast."""
    due_kickoffs = []
    for game in games:
        kickoff = dt(game.get("kickoff_utc") if isinstance(game, dict) else None)
        if kickoff is None:
            continue
        minutes = (kickoff - now).total_seconds() / 60
        if MIN_MINUTES <= minutes <= MAX_MINUTES:
            due_kickoffs.append(kickoff)
    if not due_kickoffs or generated is None or generated > now:
        return False
    return all(kickoff - FORECAST_FRESH <= generated < kickoff for kickoff in due_kickoffs)


def main():
    path = Path("data/live-v2.json")
    data = json.loads(path.read_text()) if path.exists() else {}
    games = data.get("games", [])
    now = datetime.now(timezone.utc)
    generated = dt(data.get("generated_at_utc"))
    if due(games, now):
        if recently_refreshed(data, now) and due_games_covered(games, generated, now):
            print("A fresh forecast already covers this kickoff; skipping a duplicate refresh")
            raise SystemExit(1)
        print(f"Forecast refresh due: kickoff is {MIN_MINUTES}–{MAX_MINUTES} minutes away")
        return
    print(f"No kickoff {MIN_MINUTES}–{MAX_MINUTES} minutes away")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
