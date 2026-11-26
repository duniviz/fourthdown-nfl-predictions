#!/usr/bin/env python3
"""Leak-free 2025 backtest of the Confidence Pool score simulation.

Each forecast is built before its game using the existing V2 replay. The
Confidence Pool simulation then uses the same score-draw process as
live/simulate.py. This research script never changes live forecasts.
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.v2 import build_v2_predictions
from live.simulate import DRAWS, simulate_games

def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None

def team_epa_rows(pbp):
    buckets = defaultdict(lambda: {"off": [], "def": []})
    for row in pbp:
        try:
            if row.get("play_type") not in ("pass", "run"):
                continue
            season, week, game_id = int(row["season"]), int(row["week"]), str(row["game_id"])
            epa = number(row.get("epa"))
            if epa is None:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        if row.get("posteam"):
            buckets[(season, week, game_id, row["posteam"])]["off"].append(epa)
        if row.get("defteam"):
            buckets[(season, week, game_id, row["defteam"])]["def"].append(epa)
    return [
        {"season": season, "week": week, "game_id": game_id, "team": team,
         "offense_epa": sum(values["off"]) / len(values["off"]),
         "defense_epa": sum(values["def"]) / len(values["def"])}
        for (season, week, game_id, team), values in buckets.items()
        if values["off"] and values["def"]
    ]

def brier(rows):
    return round(sum((row["confidence"] - row["won"]) ** 2 for row in rows) / len(rows), 4) if rows else None

def calibration(rows):
    bins = [(0.50, 0.60), (0.60, 0.70), (0.70, 0.80), (0.80, 0.90), (0.90, 1.01)]
    result = []
    for low, high in bins:
        group = [row for row in rows if low <= row["confidence"] < high]
        if group:
            result.append({
                "bin": f"{int(low * 100)}–{int(min(high, 1.0) * 100) - 1}%",
                "games": len(group),
                "mean_model_confidence": round(100 * sum(row["confidence"] for row in group) / len(group), 1),
                "actual_winner_rate": round(100 * sum(row["won"] for row in group) / len(group), 1),
            })
    return result

def summarize(rows):
    ordered = sorted(rows, key=lambda row: row["confidence"], reverse=True)
    def accuracy(group):
        return round(100 * sum(row["won"] for row in group) / len(group), 1) if group else None
    top_quarter = ordered[:max(1, math.ceil(len(ordered) / 4))]
    return {
        "games": len(rows),
        "winner_accuracy_pct": accuracy(rows),
        "brier_score": brier(rows),
        "mean_confidence_pct": round(100 * sum(row["confidence"] for row in rows) / len(rows), 1) if rows else None,
        "top_quarter_by_confidence": {
            "games": len(top_quarter),
            "winner_accuracy_pct": accuracy(top_quarter),
            "mean_confidence_pct": round(100 * sum(row["confidence"] for row in top_quarter) / len(top_quarter), 1) if top_quarter else None,
        },
        "calibration": calibration(rows),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--season", type=int, default=2025)
    args = parser.parse_args()
    seasons = [args.season - 1, args.season]
    import nflreadpy as nfl
    schedules = nfl.load_schedules(seasons).to_dicts()
    pbp = nfl.load_pbp(seasons).to_dicts()
    predictions = build_v2_predictions(schedules, team_epa_rows(pbp))
    holdout = [row for row in predictions if row["season"] == args.season and row["actual_margin"] != 0]
    simulations = simulate_games([
        {"game_id": row["game_id"], "home": row["home_team"], "away": row["away_team"],
         "projected_home_score": (row["pred_total"] + row["pred_margin"]) / 2,
         "projected_away_score": (row["pred_total"] - row["pred_margin"]) / 2}
        for row in holdout
    ])
    by_game = {str(row["game_id"]): row for row in simulations}
    rows = []
    for forecast in holdout:
        sim = by_game[str(forecast["game_id"])]
        home_pick = sim["home_win_pct"] >= sim["away_win_pct"]
        confidence = (sim["home_win_pct"] if home_pick else sim["away_win_pct"]) / 100
        home_won = forecast["actual_margin"] > 0
        rows.append({
            "game_id": str(forecast["game_id"]), "week": forecast["week"],
            "projected_winner": forecast["home_team"] if home_pick else forecast["away_team"],
            "confidence": confidence,
            "won": int(home_pick == home_won),
        })
    result = {
        "status": "research_only_historical_replay",
        "season": args.season,
        "simulation_draws_per_game": DRAWS,
        "results": summarize(rows),
        "limitations": [
            "Forecasts are leak-free V2 replays: only prior completed games inform each forecast.",
            "The score-draw distribution is exploratory and has not been calibrated to historical outcome probabilities.",
            "This evaluates winner confidence only; it does not evaluate ATS, totals, or betting profitability.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
