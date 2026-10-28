#!/usr/bin/env python3
"""Leak-free 2025 V2 replay against supplied closing spreads and totals.

The score model never sees the betting lines. Lines are used only after each
pregame forecast has been generated to grade ATS and over/under results.
"""
import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.v2 import build_v2_predictions

EDGE_THRESHOLDS = (0.0, 1.0, 1.5, 2.0, 3.0, 4.0)

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

def read_lines(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    clean = []
    for row in rows:
        try:
            week = int(str(row["Week"]).replace("Week", "").strip())
            away, home = row["Away Team"].strip().upper(), row["Home Team"].strip().upper()
            spread, total = number(row["Closing Spread"]), number(row["Closing O/U"])
            away_score, home_score = number(row["Away Score"]), number(row["Home Score"])
            if not all((away, home)) or None in (spread, total, away_score, home_score):
                continue
            clean.append({"week": week, "away": away, "home": home, "home_spread": spread,
                          "total_line": total, "away_score": away_score, "home_score": home_score,
                          "source_ats": row.get("ATS Winner", "").strip().upper(),
                          "source_ou": row.get("O/U Result", "").strip().title()})
        except (KeyError, AttributeError, ValueError):
            continue
    return clean

def grade(selection, result):
    if result == "push":
        return "push"
    return "win" if selection == result else "loss"

def summarize(records):
    wins = sum(row["grade"] == "win" for row in records)
    losses = sum(row["grade"] == "loss" for row in records)
    pushes = sum(row["grade"] == "push" for row in records)
    decisions = wins + losses
    return {
        "picks": len(records), "wins": wins, "losses": losses, "pushes": pushes,
        "win_rate_pct": round(100 * wins / decisions, 1) if decisions else None,
        "mean_model_edge_points": round(sum(abs(row["edge"]) for row in records) / len(records), 2) if records else None,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=ROOT / "research/nfl_2025_season_betting_results.csv")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--season", type=int, default=2025)
    args = parser.parse_args()

    lines = read_lines(args.csv)
    by_matchup = {(row["week"], row["away"], row["home"]): row for row in lines}
    import nflreadpy as nfl
    seasons = [args.season - 1, args.season]
    schedules = nfl.load_schedules(seasons).to_dicts()
    predictions = build_v2_predictions(schedules, team_epa_rows(nfl.load_pbp(seasons).to_dicts()))
    holdout = [row for row in predictions if row["season"] == args.season]
    matched, source_mismatches = [], []
    for forecast in holdout:
        line = by_matchup.get((forecast["week"], forecast["away_team"], forecast["home_team"]))
        if not line:
            continue
        actual_margin = forecast["actual_margin"]
        actual_total = forecast["actual_total"]
        ats_result = "home" if actual_margin + line["home_spread"] > 0 else "away" if actual_margin + line["home_spread"] < 0 else "push"
        ou_result = "over" if actual_total > line["total_line"] else "under" if actual_total < line["total_line"] else "push"
        expected_ats = forecast["home_team"] if ats_result == "home" else forecast["away_team"] if ats_result == "away" else "PUSH"
        expected_ou = ou_result.title()
        if line["source_ats"] != expected_ats or line["source_ou"] != expected_ou:
            source_mismatches.append({"week": forecast["week"], "away": forecast["away_team"], "home": forecast["home_team"],
                                      "csv_ats": line["source_ats"], "computed_ats": expected_ats,
                                      "csv_ou": line["source_ou"], "computed_ou": expected_ou})
        matched.append({"forecast": forecast, "line": line, "ats_result": ats_result, "ou_result": ou_result})

    threshold_results = {}
    for threshold in EDGE_THRESHOLDS:
        ats, totals = [], []
        for row in matched:
            forecast, line = row["forecast"], row["line"]
            ats_edge = forecast["pred_margin"] + line["home_spread"]
            if abs(ats_edge) > threshold:
                selection = "home" if ats_edge > 0 else "away"
                ats.append({"edge": ats_edge, "grade": grade(selection, row["ats_result"])})
            total_edge = forecast["pred_total"] - line["total_line"]
            if abs(total_edge) > threshold:
                selection = "over" if total_edge > 0 else "under"
                totals.append({"edge": total_edge, "grade": grade(selection, row["ou_result"])})
        threshold_results[str(threshold)] = {"ats": summarize(ats), "over_under": summarize(totals)}

    minimum_matches = 200
    valid_match = len(matched) >= minimum_matches
    result = {
        "status": "research_only_historical_replay" if valid_match else "invalid_schedule_alignment",
        "season": args.season,
        "source_csv_rows": len(lines),
        "eligible_pregame_v2_forecasts": len(holdout),
        "matched_forecasts": len(matched),
        "unmatched_forecasts": len(holdout) - len(matched),
        "source_result_mismatches": source_mismatches,
        "edge_thresholds": threshold_results,
        "conventions": {
            "closing_spread": "CSV Closing Spread is interpreted as the home team's point spread; this is validated against supplied ATS Winner.",
            "ats_edge": "projected home margin plus home closing spread; positive selects home, negative selects away.",
            "total_edge": "projected total minus closing total; positive selects over, negative selects under.",
        },
        "limitations": [
            "The CSV has closing lines but not odds/juice, so ROI and break-even-after-vig are not reported.",
            "Thresholds are reported side by side; none are selected or optimized on the 2025 holdout.",
            "The score model does not use these lines as inputs.",
            "A valid evaluation requires at least 200 matchup-aligned closing-line rows.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
