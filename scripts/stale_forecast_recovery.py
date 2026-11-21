"""Safely recover a missed daily forecast using the existing scheduled ticks."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from live.game_pregame_observations import dt


def recovery_due(slate, now):
    if now.tzinfo is None or not isinstance(slate, dict):
        return False
    games = slate.get("games")
    if not isinstance(games, list) or not games:
        return False
    kicks = [dt(game.get("kickoff_utc")) if isinstance(game, dict) else None for game in games]
    if any(k is None for k in kicks):
        return False
    # Never start a recovery during a game or close to another kickoff.
    if any(now - timedelta(hours=4) < kick <= now + timedelta(minutes=150) for kick in kicks):
        return False
    # Do not generate stale archived/offseason slates.
    if not any(now < kick <= now + timedelta(days=7) for kick in kicks):
        return False
    generated = dt(slate.get("generated_at_utc"))
    if generated and generated > now:
        return False
    return generated is None or now - generated >= timedelta(hours=30)


def main():
    try:
        slate = json.loads(Path("data/live-v2.json").read_text())
        due = recovery_due(slate, datetime.now(timezone.utc))
    except (OSError, ValueError, TypeError, AttributeError):
        due = False
    print("Stale forecast recovery due" if due else "No safe stale forecast recovery due")
    return 0 if due else 1


if __name__ == "__main__":
    raise SystemExit(main())
