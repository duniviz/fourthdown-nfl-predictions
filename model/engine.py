"""Transparent baseline NFL game simulator. No trained claims or sportsbook feeds."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
import random

@dataclass(frozen=True)
class TeamRating:
    team: str
    offense: float = 0.0  # points per game above league average
    defense: float = 0.0  # points allowed per game below league average (positive is good)

@dataclass(frozen=True)
class GameInput:
    away: TeamRating
    home: TeamRating
    home_advantage: float = 1.5
    league_points: float = 22.0
    pace_factor: float = 1.0
    # Explicit pregame adjustments in points, e.g. injury/weather; caller must justify inputs
    away_adjustment: float = 0.0
    home_adjustment: float = 0.0

def expected_scores(game: GameInput) -> tuple[float, float]:
    if game.pace_factor <= 0 or game.league_points <= 0:
        raise ValueError("pace_factor and league_points must be positive")
    away = (game.league_points + game.away.offense - game.home.defense
            + game.away_adjustment) * game.pace_factor
    home = (game.league_points + game.home.offense - game.away.defense
            + game.home_adjustment + game.home_advantage) * game.pace_factor
    return max(0.1, away), max(0.1, home)

def simulate(game: GameInput, n: int = 5000, seed: int = 42,
             spread_home: float | None = None, total_line: float | None = None,
             score_sd: float = 10.5, shared_sd: float = 3.0) -> dict:
    """Simulate correlated scores; ATS uses home score + home spread > away score.

    This is an *uncalibrated research baseline*, not a validated betting probability.
    Scores are normal draws, rounded to nonnegative integers; ties count as ties.
    """
    if not 1 <= n <= 1_000_000:
        raise ValueError("n must be between 1 and 1,000,000")
    if score_sd <= 0 or not 0 <= shared_sd < score_sd:
        raise ValueError("require score_sd > shared_sd >= 0")
    rng = random.Random(seed)
    mu_away, mu_home = expected_scores(game)
    independent_sd = math.sqrt(score_sd ** 2 - shared_sd ** 2)
    home_wins = away_wins = ties = home_covers = away_covers = pushes = overs = unders = total_pushes = 0
    sum_home = sum_away = 0
    for _ in range(n):
        shared = rng.gauss(0, shared_sd)
        away = max(0, round(mu_away + shared + rng.gauss(0, independent_sd)))
        home = max(0, round(mu_home + shared + rng.gauss(0, independent_sd)))
        sum_away += away
        sum_home += home
        home_wins += home > away
        away_wins += away > home
        ties += home == away
        if spread_home is not None:
            margin = home + spread_home - away
            home_covers += margin > 0
            away_covers += margin < 0
            pushes += margin == 0
        if total_line is not None:
            total = home + away
            overs += total > total_line
            unders += total < total_line
            total_pushes += total == total_line
    result = {
        "away": game.away.team, "home": game.home.team, "simulations": n, "seed": seed,
        "expected_away": round(mu_away, 2), "expected_home": round(mu_home, 2),
        "simulated_mean_away": round(sum_away / n, 2),
        "simulated_mean_home": round(sum_home / n, 2),
        "home_win_probability": round(home_wins / n, 4),
        "away_win_probability": round(away_wins / n, 4),
        "tie_probability": round(ties / n, 4),
        "status": "uncalibrated_baseline"
    }
    if spread_home is not None:
        result["spread_home"] = spread_home
        result["home_cover_probability"] = round(home_covers / n, 4)
        result["away_cover_probability"] = round(away_covers / n, 4)
        result["spread_push_probability"] = round(pushes / n, 4)
    if total_line is not None:
        result["total_line"] = total_line
        result["over_probability"] = round(overs / n, 4)
        result["under_probability"] = round(unders / n, 4)
        result["total_push_probability"] = round(total_pushes / n, 4)
    return result
