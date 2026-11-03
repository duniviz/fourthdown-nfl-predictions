#!/usr/bin/env python3
"""Generate a locked, research-only v3 score-model shadow.

The shadow deliberately never modifies data/live-v2.json.  It uses only
pre-kickoff v2 forecasts and features calculated from completed prior weeks.
Its coefficients are hypotheses to be evaluated from immutable snapshots,
not production parameters or betting recommendations.
"""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

MODEL = "FOURTHDOWN v3 feature shadow"
# Predeclared research hypotheses.  They must not be tuned using current-week
# results; promotion requires the separately archived, chronological evaluation.
PACE_POINTS_PER_PLAY = 0.10
SUCCESS_MARGIN_POINTS = 8.0
PASS_MARGIN_POINTS = 2.0
MAX_TOTAL_ADJUSTMENT = 3.0
MAX_MARGIN_ADJUSTMENT = 3.0

def finite(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None

def bounded(value, limit):
    return max(-limit, min(limit, value))

def league_means(features):
    values = {}
    for key in ("plays_per_game", "success_rate", "neutral_pass_proxy"):
        rows = [finite(team.get(key)) for team in features.values()]
        rows = [value for value in rows if value is not None]
        if not rows:
            raise ValueError(f"No usable {key} feature values")
        values[key] = sum(rows) / len(rows)
    return values

def project(v2, features, generated_at):
    if not isinstance(v2.get("games"), list) or not v2["games"]:
        raise ValueError("v2 input has no games")
    team_features = features.get("features")
    if not isinstance(team_features, dict) or not team_features:
        raise ValueError("feature input has no team features")
    means = league_means(team_features)
    games = []
    for base in v2["games"]:
        home, away = base.get("home"), base.get("away")
        home_f, away_f = team_features.get(home), team_features.get(away)
        if not isinstance(home_f, dict) or not isinstance(away_f, dict):
            continue
        home_plays, away_plays = finite(home_f.get("plays_per_game")), finite(away_f.get("plays_per_game"))
        home_success, away_success = finite(home_f.get("success_rate")), finite(away_f.get("success_rate"))
        home_pass, away_pass = finite(home_f.get("neutral_pass_proxy")), finite(away_f.get("neutral_pass_proxy"))
        if None in (home_plays, away_plays, home_success, away_success, home_pass, away_pass):
            continue
        total_adjustment = bounded(
            PACE_POINTS_PER_PLAY * ((home_plays + away_plays) - 2 * means["plays_per_game"]),
            MAX_TOTAL_ADJUSTMENT,
        )
        margin_adjustment = bounded(
            SUCCESS_MARGIN_POINTS * (home_success - away_success)
            + PASS_MARGIN_POINTS * (home_pass - away_pass),
            MAX_MARGIN_ADJUSTMENT,
        )
        total = max(1.0, finite(base.get("projected_total")) + total_adjustment)
        margin = finite(base.get("projected_margin_home")) + margin_adjustment
        home_score, away_score = max(0.0, (total + margin) / 2), max(0.0, (total - margin) / 2)
        games.append({
            "game_id": base["game_id"], "season": base["season"], "week": base["week"],
            "kickoff_utc": base["kickoff_utc"], "home": home, "away": away,
            "projected_home_score": round(home_score, 1), "projected_away_score": round(away_score, 1),
            "projected_margin_home": round(home_score - away_score, 2),
            "projected_total": round(home_score + away_score, 2),
            "predicted_winner": home if home_score > away_score else away,
            "v2_reference": {
                "projected_margin_home": base["projected_margin_home"],
                "projected_total": base["projected_total"],
            },
            "feature_adjustments": {
                "total_from_pace": round(total_adjustment, 3),
                "margin_from_success_and_pass_proxy": round(margin_adjustment, 3),
                "home_features": {k: home_f.get(k) for k in ("plays_per_game", "success_rate", "neutral_pass_proxy")},
                "away_features": {k: away_f.get(k) for k in ("plays_per_game", "success_rate", "neutral_pass_proxy")},
            },
        })
    if not games:
        raise ValueError("No v3 shadow games had complete pregame features")
    return {
        "model": MODEL, "generated_at_utc": generated_at,
        "season": v2.get("season"), "week": v2.get("week"),
        "status": "research_only_not_for_live_or_betting_use",
        "production_change_approved": False,
        "coefficients": {
            "pace_points_per_play": PACE_POINTS_PER_PLAY,
            "success_margin_points": SUCCESS_MARGIN_POINTS,
            "pass_margin_points": PASS_MARGIN_POINTS,
            "max_total_adjustment": MAX_TOTAL_ADJUSTMENT,
            "max_margin_adjustment": MAX_MARGIN_ADJUSTMENT,
        },
        "limitations": [
            "Uses a pass-play proxy, not verified neutral-situation pass rate.",
            "Weather and non-QB injuries are collected separately and are not numerically adjusted.",
            "Coefficients are fixed research hypotheses; they are not fitted or promoted.",
            "Evaluate only against the first immutable pre-kickoff snapshot.",
        ],
        "games": games,
    }

def update_history(history_path, shadow):
    history = {"model": MODEL, "games": []}
    if history_path.exists():
        history = json.loads(history_path.read_text(encoding="utf-8"))
    existing = {str(game.get("game_id")) for game in history.get("games", [])}
    for game in shadow["games"]:
        if str(game["game_id"]) not in existing:
            history["games"].append({**game, "published_at_utc": shadow["generated_at_utc"]})
    return history

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--v2", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    args = parser.parse_args()
    now = datetime.now(timezone.utc).isoformat()
    v2 = json.loads(args.v2.read_text(encoding="utf-8"))
    features = json.loads(args.features.read_text(encoding="utf-8"))
    shadow = project(v2, features, now)
    history = update_history(args.history, shadow)
    args.output.write_text(json.dumps(shadow, indent=2) + "\n", encoding="utf-8")
    args.history.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(shadow['games'])} v3 shadow forecasts; production unchanged.")

if __name__ == "__main__":
    main()
