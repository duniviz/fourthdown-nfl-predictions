#!/usr/bin/env python3
"""Leak-free V2 replay using nflverse schedule results and consensus closing lines.

The score model never sees betting lines. nflverse's historical spread_line and
total_line are used only after each pregame forecast has been generated.
These are consensus lines, not DraftKings-specific closes.
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
        {
            "season": season,
            "week": week,
            "game_id": game_id,
            "team": team,
            "offense_epa": sum(values["off"]) / len(values["off"]),
            "defense_epa": sum(values["def"]) / len(values["def"]),
        }
        for (season, week, game_id, team), values in buckets.items()
        if values["off"] and values["def"]
    ]


def consensus_lines(schedules, season, start_week, end_week):
    """Return schedule-aligned consensus lines; omit incomplete or unpriced games."""
    clean = []
    for row in schedules:
        try:
            if (
                int(row["season"]) != season
                or str(row.get("game_type", "")).upper() != "REG"
                or not start_week <= int(row["week"]) <= end_week
            ):
                continue
            week = int(row["week"])
            away, home = str(row["away_team"]).upper(), str(row["home_team"]).upper()
            spread = number(row.get("spread_line"))
            total = number(row.get("total_line"))
            away_score, home_score = number(row.get("away_score")), number(row.get("home_score"))
            if not all((away, home)) or None in (spread, total, away_score, home_score):
                continue
        except (KeyError, TypeError, ValueError):
            continue
        clean.append(
            {
                "week": week,
                "away": away,
                "home": home,
                "home_spread": spread,
                "total_line": total,
                "away_score": away_score,
                "home_score": home_score,
            }
        )
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
        "picks": len(records),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_rate_pct": round(100 * wins / decisions, 1) if decisions else None,
        "mean_model_edge_points": round(
            sum(abs(row["edge"]) for row in records) / len(records), 2
        )
        if records
        else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--start-week", type=int, default=4)
    parser.add_argument("--end-week", type=int, default=18)
    parser.add_argument("--minimum-matches", type=int, default=200)
    args = parser.parse_args()

    import nflreadpy as nfl

    seasons = [args.season - 1, args.season]
    schedules = nfl.load_schedules(seasons).to_dicts()
    lines = consensus_lines(schedules, args.season, args.start_week, args.end_week)
    by_matchup = {(row["week"], row["away"], row["home"]): row for row in lines}
    predictions = build_v2_predictions(schedules, team_epa_rows(nfl.load_pbp(seasons).to_dicts()))
    holdout = [
        row
        for row in predictions
        if row["season"] == args.season
        and args.start_week <= row["week"] <= args.end_week
    ]

    matched, result_mismatches = [], []
    for forecast in holdout:
        line = by_matchup.get((forecast["week"], forecast["away_team"], forecast["home_team"]))
        if not line:
            continue
        actual_margin = forecast["actual_margin"]
        actual_total = forecast["actual_total"]
        expected_margin = line["home_score"] - line["away_score"]
        expected_total = line["home_score"] + line["away_score"]
        if actual_margin != expected_margin or actual_total != expected_total:
            result_mismatches.append(
                {
                    "week": forecast["week"],
                    "away": forecast["away_team"],
                    "home": forecast["home_team"],
                    "forecast_margin": actual_margin,
                    "schedule_margin": expected_margin,
                    "forecast_total": actual_total,
                    "schedule_total": expected_total,
                }
            )
            continue
        ats_result = "home" if actual_margin + line["home_spread"] > 0 else "away" if actual_margin + line["home_spread"] < 0 else "push"
        ou_result = "over" if actual_total > line["total_line"] else "under" if actual_total < line["total_line"] else "push"
        matched.append({"forecast": forecast, "line": line, "ats_result": ats_result, "ou_result": ou_result})

    threshold_results = {}
    for threshold in EDGE_THRESHOLDS:
        ats, totals = [], []
        for row in matched:
            forecast, line = row["forecast"], row["line"]
            ats_edge = forecast["pred_margin"] + line["home_spread"]
            if abs(ats_edge) > threshold:
                ats.append(
                    {
                        "edge": ats_edge,
                        "grade": grade("home" if ats_edge > 0 else "away", row["ats_result"]),
                    }
                )
            total_edge = forecast["pred_total"] - line["total_line"]
            if abs(total_edge) > threshold:
                totals.append(
                    {
                        "edge": total_edge,
                        "grade": grade("over" if total_edge > 0 else "under", row["ou_result"]),
                    }
                )
        threshold_results[str(threshold)] = {
            "ats": summarize(ats),
            "over_under": summarize(totals),
        }

    valid_match = len(matched) >= args.minimum_matches
    result = {
        "status": "research_only_historical_replay" if valid_match else "invalid_schedule_alignment",
        "season": args.season,
        "weeks": [args.start_week, args.end_week],
        "line_source": "nflverse schedule spread_line and total_line (historical consensus; not DraftKings-specific)",
        "eligible_pregame_v2_forecasts": len(holdout),
        "schedule_rows_with_lines": len(lines),
        "matched_forecasts": len(matched),
        "unmatched_forecasts": len(holdout) - len(matched),
        "score_result_mismatches": result_mismatches,
        "edge_thresholds": threshold_results,
        "conventions": {
            "home_spread": "nflverse spread_line, expressed for the home team.",
            "ats_edge": "projected home margin plus home closing spread; positive selects home, negative selects away.",
            "total_edge": "projected total minus consensus closing total; positive selects over, negative selects under.",
        },
        "limitations": [
            "These are historical consensus lines, not exact DraftKings closing lines.",
            "Odds/juice are not available here, so ROI and break-even-after-vig are not reported.",
            "Thresholds are reported side by side; none are selected or optimized on the 2025 holdout.",
            "The score model does not use these lines as inputs.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
