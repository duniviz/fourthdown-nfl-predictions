"""Match provider events to the published slate despite small kickoff-time drift."""
from datetime import timedelta
from live.game_pregame_observations import dt


def match_scheduled_game(games, home, away, kickoff, tolerance_minutes=15):
    """Return one uniquely matching published game; reject ambiguous or distant events."""
    provider_kickoff = dt(kickoff)
    if not provider_kickoff or not home or not away:
        return None
    candidates = []
    for game in games:
        if game.get("home") != home or game.get("away") != away:
            continue
        scheduled_kickoff = dt(game.get("kickoff_utc"))
        if scheduled_kickoff and abs(scheduled_kickoff - provider_kickoff) <= timedelta(minutes=tolerance_minutes):
            candidates.append(game)
    return candidates[0] if len(candidates) == 1 else None
