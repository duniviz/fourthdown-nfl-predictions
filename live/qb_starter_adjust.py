"""Conservative score adjustment for a new starting QB.

This is an experimental, capped adjustment. Team EPA already reflects prior
team QB play; only a starter with fewer than two prior games for the team is
treated as an incoming QB. The player's recent same-season production is
compared with the team's prior QB mix. No adjustment is applied without enough
prior-game data.
"""
import json
import math
from collections import defaultdict
from pathlib import Path

CAP_POINTS = 2.0
POINTS_PER_EFFICIENCY_UNIT = 0.45
MIN_GAMES = 2


def _normalize(value):
    return " ".join(str(value or "").lower().replace(".", "").split())


def _number(value):
    try:
        result = float(value or 0)
        return result if math.isfinite(result) else 0.0
    except (TypeError, ValueError):
        return 0.0


def load_qb_starters(season, path="data/verified-starters.json"):
    """Map current-season game/team QB starter records to names and statuses."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    rows = payload.get("starters", []) if isinstance(payload, dict) else []
    result = {}
    priority = {"projected": 1, "confirmed": 2}
    for row in rows:
        if not isinstance(row, dict) or str(row.get("position", "")).upper() != "QB":
            continue
        try:
            if int(row.get("season", -1)) != season:
                continue
        except (TypeError, ValueError):
            continue
        status = str(row.get("status", "")).lower()
        team = str(row.get("team") or "").upper()
        game_id = str(row.get("game_id") or "")
        player = str(row.get("player") or "").strip()
        if status not in priority or not team or not game_id or not player:
            continue
        key = (game_id, team)
        prior = result.get(key)
        if prior is None or priority[status] > priority[prior["status"]]:
            result[key] = {"player": player, "status": status}
    return result


def _rating(rows):
    by_week = defaultdict(list)
    for row in rows:
        attempts = _number(row.get("attempts"))
        if attempts < 8:
            continue
        efficiency = (
            _number(row.get("passing_yards"))
            + _number(row.get("rushing_yards"))
            + 20 * _number(row.get("passing_tds"))
            - 35 * _number(row.get("interceptions"))
        ) / attempts
        by_week[int(row["week"])].append((efficiency, attempts))
    games = len(by_week)
    if not games:
        return None, 0
    attempts = sum(a for vals in by_week.values() for _, a in vals)
    return sum(e * a for vals in by_week.values() for e, a in vals) / attempts, games


def estimate_starter_adjustment(team, starter, weekly_stats, schedules, target_week, season):
    """Estimate score delta for a new-to-team QB; output remains explicitly low confidence."""
    base = {
        "points": 0.0,
        "status": "starter_context_unavailable",
        "players": [],
        "confidence": "low",
    }
    if not isinstance(starter, dict) or not starter.get("player"):
        return base
    status = str(starter.get("status") or "").lower()
    if status not in {"confirmed", "projected"}:
        base["status"] = "starter_status_unusable"
        return base

    completed = set()
    for game in schedules:
        if str(game.get("game_type") or "") != "REG":
            continue
        try:
            game_season = int(game.get("season", season))
            week = int(game.get("week"))
        except (TypeError, ValueError):
            continue
        if game_season != season or week >= target_week:
            continue
        if game.get("home_score") is None or game.get("away_score") is None:
            continue
        completed.add((week, str(game.get("home_team") or "").upper()))
        completed.add((week, str(game.get("away_team") or "").upper()))
    stats = []
    for row in weekly_stats or []:
        if str(row.get("position") or "").upper() != "QB":
            continue
        try:
            week = int(row.get("week"))
            row_season = int(row.get("season", season))
        except (TypeError, ValueError):
            continue
        row_team = str(row.get("team") or "").upper()
        if row_season != season or (week, row_team) not in completed:
            continue
        if _number(row.get("attempts")) < 8:
            continue
        stats.append(row)

    starter_name = _normalize(starter["player"])
    candidate_rows = [
        row for row in stats
        if _normalize(row.get("player_display_name") or row.get("player_name")) == starter_name
    ]
    candidate_team_rows = [row for row in candidate_rows if str(row.get("team") or "").upper() == team.upper()]
    candidate_rating, candidate_games = _rating(candidate_rows)
    team_rows = [row for row in stats if str(row.get("team") or "").upper() == team.upper()]
    team_rating, team_games = _rating(team_rows)

    if len({int(r["week"]) for r in candidate_team_rows}) >= MIN_GAMES:
        base["status"] = "starter_already_in_team_baseline"
        return base
    if candidate_rating is None or candidate_games < MIN_GAMES:
        base["status"] = "incoming_starter_insufficient_prior_games"
        return base
    if team_rating is None or team_games < MIN_GAMES:
        base["status"] = "team_qb_baseline_insufficient_prior_games"
        return base

    raw = (candidate_rating - team_rating) * POINTS_PER_EFFICIENCY_UNIT
    points = max(-CAP_POINTS, min(CAP_POINTS, raw))
    return {
        "points": round(points, 2),
        "status": "experimental_incoming_qb_adjustment",
        "players": [{
            "player": starter["player"],
            "starter_status": status,
            "prior_games": candidate_games,
            "adjustment_points": round(points, 2),
        }],
        "method": "recent same-season QB efficiency versus the team's prior QB mix",
        "confidence": "low",
        "cap_points": CAP_POINTS,
    }
