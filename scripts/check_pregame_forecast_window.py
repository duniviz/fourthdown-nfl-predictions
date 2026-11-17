"""Allow a full forecast refresh 80–150 minutes before a published kickoff."""
import json
from datetime import datetime, timezone
from pathlib import Path
from live.game_pregame_observations import dt

MIN_MINUTES = 80
MAX_MINUTES = 150
FRESH_MINUTES = 45


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


def main():
    path = Path("data/live-v2.json")
    data = json.loads(path.read_text()) if path.exists() else {}
    games = data.get("games", [])
    now = datetime.now(timezone.utc)
    if recently_refreshed(data, now):
        print("Forecast was refreshed within the last 45 minutes; skipping duplicate tick")
        raise SystemExit(1)
    if due(games, now):
        print(f"Pregame forecast refresh due ({MIN_MINUTES}–{MAX_MINUTES} minutes before kickoff)")
        return
    print(f"No kickoff {MIN_MINUTES}–{MAX_MINUTES} minutes away")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
