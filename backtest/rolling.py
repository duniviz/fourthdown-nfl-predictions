"""Leakage-safe weekly backtest using nflverse schedules and team EPA by game.

Inputs are CSV files. Features for a given week are computed only from earlier
weeks, with season resets and a neutral preseason prior.
"""
import csv
import math
from collections import defaultdict
from pathlib import Path

def load_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def _number(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None

def build_rolling_predictions(schedules, team_games, min_games=3, prior_weight=4.0):
    """Return one pregame prediction per completed regular-season game.

    team_games rows: season,week,team,offense_epa,defense_epa
    defense_epa is *opponent offensive EPA per play*, so lower is better.
    Schedules rows: season,week,game_id,home_team,away_team,home_score,away_score,game_type.
    """
    if min_games < 0 or prior_weight < 0:
        raise ValueError("min_games and prior_weight must be nonnegative")
    by_week = defaultdict(list)
    for row in team_games:
        season, week = int(row["season"]), int(row["week"])
        if week < 1: continue
        off, deff = _number(row.get("offense_epa")), _number(row.get("defense_epa"))
        if off is None or deff is None: continue
        by_week[(season, week)].append((row["team"], off, deff))
    games = defaultdict(list)
    for row in schedules:
        if row.get("game_type", "REG") != "REG": continue
        if _number(row.get("home_score")) is None or _number(row.get("away_score")) is None: continue
        games[(int(row["season"]), int(row["week"]))].append(row)
    ratings = defaultdict(lambda: [0.0, 0.0, 0])
    output = []
    for season, week in sorted(set(games) | set(by_week)):
        # Crucial: predict *before* incorporating this week's games.
        for row in games.get((season, week), []):
            home, away = row["home_team"], row["away_team"]
            h = ratings[(season, home)]
            a = ratings[(season, away)]
            if h[2] < min_games or a[2] < min_games: continue
            h_off = h[0] / (h[2] + prior_weight)
            h_def = h[1] / (h[2] + prior_weight)
            a_off = a[0] / (a[2] + prior_weight)
            a_def = a[1] / (a[2] + prior_weight)
            # Points-per-play conversion is an initial hypothesis, not fitted.
            # A positive defense EPA means a weaker defense.
            pred_margin = 1.5 + 45.0 * ((h_off - a_def) - (a_off - h_def))
            pred_total = 44.0 + 45.0 * ((h_off - a_def) + (a_off - h_def))
            actual_margin = float(row["home_score"]) - float(row["away_score"])
            actual_total = float(row["home_score"]) + float(row["away_score"])
            output.append({
                "season": season, "week": week, "game_id": row["game_id"],
                "home_team": home, "away_team": away,
                "pred_margin": round(pred_margin, 4),
                "pred_total": round(max(1.0, pred_total), 4),
                "actual_margin": actual_margin, "actual_total": actual_total,
                "home_win": int(actual_margin > 0),
                "home_spread": _number(row.get("spread_line")),
                "market_total": _number(row.get("total_line")),
            })
        for team, off, deff in by_week.get((season, week), []):
            r = ratings[(season, team)]
            r[0] += off
            r[1] += deff
            r[2] += 1
    return output

def summarize(predictions):
    if not predictions:
        return {"games": 0, "status": "no_eligible_games"}
    n = len(predictions)
    winner_correct = sum((r["pred_margin"] > 0) == (r["actual_margin"] > 0) for r in predictions if r["actual_margin"] != 0)
    non_ties = sum(r["actual_margin"] != 0 for r in predictions)
    return {
        "games": n,
        "winner_accuracy_excluding_ties": round(winner_correct / non_ties, 4) if non_ties else None,
        "margin_mae": round(sum(abs(r["pred_margin"] - r["actual_margin"]) for r in predictions) / n, 3),
        "total_mae": round(sum(abs(r["pred_total"] - r["actual_total"]) for r in predictions) / n, 3),
        "status": "unfitted_baseline_not_validated",
    }
