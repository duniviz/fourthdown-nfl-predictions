"""Decide whether the daily 5 PM Central forecast is safely ahead of kickoff."""
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from live.game_pregame_observations import dt

CENTRAL = ZoneInfo("America/Chicago")
MIN_KICKOFF_BUFFER_MINUTES = 90


def daily_run_allowed(games, now, minimum_buffer=MIN_KICKOFF_BUFFER_MINUTES):
    """Run on non-game dates, or on game dates with a safe buffer before kickoff."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if not games:
        return False, "No slate available to verify forecast timing"

    parsed_kickoffs = [kickoff for game in games if (kickoff := dt(game.get("kickoff_utc"))) is not None]
    if not parsed_kickoffs:
        return False, "No valid kickoff found in the slate"

    today = now.astimezone(CENTRAL).date()
    today_kickoffs = [
        kickoff for kickoff in parsed_kickoffs
        if kickoff.astimezone(CENTRAL).date() == today
    ]

    if not today_kickoffs:
        return True, "No NFL game scheduled today"
    future = [kickoff for kickoff in today_kickoffs if kickoff > now]
    if not future:
        return False, "Today's kickoffs have started"
    minutes = (min(future) - now).total_seconds() / 60
    if minutes < minimum_buffer:
        return False, f"Next kickoff is only {minutes:.0f} minutes away"
    return True, f"Next kickoff is {minutes:.0f} minutes away"


def main():
    path = Path("data/live-v2.json")
    data = json.loads(path.read_text()) if path.exists() else {}
    now = datetime.now(timezone.utc)
    allowed, reason = daily_run_allowed(data.get("games", []), now)
    print(reason)
    if not allowed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
