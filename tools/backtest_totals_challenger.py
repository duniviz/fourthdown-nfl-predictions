#!/usr/bin/env python3
"""Leakage-safe totals challenger: pass EPA, positive-EPA rate, and play volume.

Training uses only completed 2022-2024 seasons. The locked evaluation is 2025
Weeks 4-18. Market totals are used solely for post-prediction grading.
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.v2 import build_v2_predictions


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def team_week_metrics(pbp):
    """Aggregate pregame-eligible play metrics by team and game week."""
    buckets = defaultdict(lambda: defaultdict(list))
    for row in pbp:
        try:
            if row.get("play_type") not in ("pass", "run"):
                continue
            season, week = int(row["season"]), int(row["week"])
            epa = number(row.get("epa"))
            if epa is None:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        game_id = str(row.get("game_id", ""))
        if row.get("posteam"):
            key = (season, week, game_id, str(row["posteam"]))
            buckets[key]["off_epa"].append(epa)
            buckets[key]["off_success"].append(float(epa > 0))
            if row.get("play_type") == "pass":
                buckets[key]["off_pass_epa"].append(epa)
        if row.get("defteam"):
            key = (season, week, game_id, str(row["defteam"]))
            buckets[key]["def_epa"].append(epa)
            buckets[key]["def_success"].append(float(epa > 0))
            if row.get("play_type") == "pass":
                buckets[key]["def_pass_epa"].append(epa)

    metrics = {}
    for (season, week, game_id, team), values in buckets.items():
        required = ("off_epa", "def_epa", "off_pass_epa", "def_pass_epa")
        if not all(values[name] for name in required):
            continue
        metrics[(season, week, team)] = {
            "off_epa": sum(values["off_epa"]) / len(values["off_epa"]),
            "def_epa": sum(values["def_epa"]) / len(values["def_epa"]),
            "off_pass_epa": sum(values["off_pass_epa"]) / len(values["off_pass_epa"]),
            "def_pass_epa": sum(values["def_pass_epa"]) / len(values["def_pass_epa"]),
            "off_success": sum(values["off_success"]) / len(values["off_success"]),
            "def_success": sum(values["def_success"]) / len(values["def_success"]),
            "off_plays": float(len(values["off_epa"])),
            "def_plays": float(len(values["def_epa"])),
        }
    return metrics


def mean_metrics(history):
    keys = tuple(history[0])
    return {key: sum(row[key] for row in history) / len(history) for key in keys}


def feature_vector(home, away):
    # Higher defensive EPA/success indicates a weaker defense.
    return [
        home["off_epa"] + away["def_epa"] + away["off_epa"] + home["def_epa"],
        home["off_pass_epa"] + away["def_pass_epa"] + away["off_pass_epa"] + home["def_pass_epa"],
        home["off_success"] + away["def_success"] + away["off_success"] + home["def_success"],
        home["off_plays"] + away["off_plays"],
    ]


def pregame_rows(schedules, metrics, seasons):
    games_by_week = defaultdict(list)
    for game in schedules:
        try:
            season, week = int(game["season"]), int(game["week"])
            if season not in seasons or str(game.get("game_type", "")).upper() != "REG":
                continue
            if number(game.get("home_score")) is None or number(game.get("away_score")) is None:
                continue
            games_by_week[(season, week)].append(game)
        except (KeyError, TypeError, ValueError):
            continue

    histories = defaultdict(list)
    rows = []
    for season, week in sorted(games_by_week):
        for game in games_by_week[(season, week)]:
            home, away = str(game["home_team"]), str(game["away_team"])
            h_history, a_history = histories[(season, home)], histories[(season, away)]
            if len(h_history) < 3 or len(a_history) < 3:
                continue
            home_mean, away_mean = mean_metrics(h_history), mean_metrics(a_history)
            rows.append(
                {
                    "season": season,
                    "week": week,
                    "game_id": str(game["game_id"]),
                    "features": feature_vector(home_mean, away_mean),
                    "actual_total": float(game["home_score"]) + float(game["away_score"]),
                    "market_total": number(game.get("total_line")),
                }
            )
        for game in games_by_week[(season, week)]:
            for team in (str(game["home_team"]), str(game["away_team"])):
                metric = metrics.get((season, week, team))
                if metric is not None:
                    histories[(season, team)].append(metric)
    return rows


def fit_ridge(rows, alpha=12.0):
    x = np.array([row["features"] for row in rows], dtype=float)
    y = np.array([row["actual_total"] for row in rows], dtype=float)
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale[scale == 0] = 1.0
    x_scaled = (x - mean) / scale
    design = np.column_stack([np.ones(len(x_scaled)), x_scaled])
    penalty = np.eye(design.shape[1]) * alpha
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    return mean, scale, coefficients


def predict(model, features):
    mean, scale, coefficients = model
    return float(np.array([1.0, *((np.array(features) - mean) / scale)]) @ coefficients)


def grade_total(predicted, actual, line):
    if actual == line:
        return "push"
    selection = "over" if predicted > line else "under"
    result = "over" if actual > line else "under"
    return "win" if selection == result else "loss"


def summary(records):
    wins = sum(row["grade"] == "win" for row in records)
    losses = sum(row["grade"] == "loss" for row in records)
    pushes = sum(row["grade"] == "push" for row in records)
    decisions = wins + losses
    return {
        "games": len(records),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate_pct": round(100 * wins / decisions, 1) if decisions else None,
        "total_mae": round(sum(abs(row["predicted"] - row["actual"]) for row in records) / len(records), 2) if records else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--start-week", type=int, default=4)
    parser.add_argument("--end-week", type=int, default=18)
    args = parser.parse_args()

    import nflreadpy as nfl

    training_seasons = [2022, 2023, 2024]
    all_seasons = training_seasons + [args.season]
    schedules = nfl.load_schedules(all_seasons).to_dicts()
    metrics = team_week_metrics(nfl.load_pbp(all_seasons).to_dicts())
    rows = pregame_rows(schedules, metrics, set(all_seasons))
    training = [row for row in rows if row["season"] in training_seasons]
    holdout = [row for row in rows if row["season"] == args.season and args.start_week <= row["week"] <= args.end_week and row["market_total"] is not None]
    model = fit_ridge(training)

    team_epa = [
        {"season": season, "week": week, "game_id": game_id, "team": team,
         "offense_epa": values["off_epa"], "defense_epa": values["def_epa"]}
        for (season, week, team), values in metrics.items()
        for game_id in [""]
    ]
    # V2 keys team EPA only by season/week/team; preserve the model's existing baseline.
    baseline = build_v2_predictions(schedules, team_epa)
    baseline_by_game = {row["game_id"]: row for row in baseline if row["season"] == args.season}

    challenger_records, baseline_records, unmatched = [], [], []
    for row in holdout:
        baseline_row = baseline_by_game.get(row["game_id"])
        if baseline_row is None:
            unmatched.append(row["game_id"])
            continue
        challenger_records.append(
            {"predicted": predict(model, row["features"]), "actual": row["actual_total"],
             "grade": grade_total(predict(model, row["features"]), row["actual_total"], row["market_total"])}
        )
        baseline_records.append(
            {"predicted": baseline_row["pred_total"], "actual": row["actual_total"],
             "grade": grade_total(baseline_row["pred_total"], row["actual_total"], row["market_total"])}
        )

    challenger_summary, baseline_summary = summary(challenger_records), summary(baseline_records)
    hit_delta = (
        challenger_summary["hit_rate_pct"] - baseline_summary["hit_rate_pct"]
        if challenger_summary["hit_rate_pct"] is not None and baseline_summary["hit_rate_pct"] is not None
        else None
    )
    result = {
        "status": "research_only_holdout_comparison",
        "training_seasons": training_seasons,
        "holdout": {"season": args.season, "weeks": [args.start_week, args.end_week]},
        "features": ["combined overall EPA", "combined passing EPA", "combined positive-EPA rate", "combined offensive plays"],
        "line_source": "nflverse historical consensus totals; not DraftKings-specific",
        "training_games": len(training),
        "holdout_games": len(holdout),
        "matched_games": len(challenger_records),
        "unmatched_game_ids": unmatched,
        "v2_baseline": baseline_summary,
        "totals_challenger": challenger_summary,
        "hit_rate_delta_percentage_points": hit_delta,
        "promotion_rule": "Candidate must improve O/U holdout hit rate by at least 1.0 percentage point on the same matched games.",
        "promotion_eligible": bool(hit_delta is not None and hit_delta >= 1.0 and len(challenger_records) >= 200),
        "limitations": [
            "This is one locked holdout comparison, not a guarantee of future performance.",
            "Historical consensus lines are used only for grading, never as model inputs.",
            "Odds/juice are unavailable, so this does not report ROI.",
            "No live model or publication file is changed by this research workflow.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
