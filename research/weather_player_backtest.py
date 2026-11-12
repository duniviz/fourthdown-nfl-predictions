#!/usr/bin/env python3
"""Research-only replay of P3 position weather splits against player yard forecasts.

This is a screening experiment. It applies the published, 50%-shrunk P3
position/category rates to historical games with observed game weather. Since
observed conditions are not the same as pregame forecasts, this report cannot
qualify a live promotion by itself.
"""
import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import nflreadpy as nfl

from live.backtest_players import backtest


SHRINKAGE = 0.5
RATES = {
    "QB": {
        "passing_yards": {
            "indoor": 0.06, "hot": -0.03, "freezing": -0.05,
            "rain": -0.09, "snow": -0.12, "windy": -0.08,
        },
    },
    "WR": {
        "receiving_yards": {
            "indoor": 0.10, "hot": -0.01, "freezing": -0.05,
            "rain": -0.10, "snow": -0.12, "windy": -0.07,
        },
        "receptions": {
            "indoor": 0.08, "hot": -0.01, "freezing": -0.05,
            "rain": -0.09, "snow": -0.09, "windy": -0.05,
        },
    },
    "TE": {
        "receiving_yards": {
            "indoor": 0.00, "hot": -0.11, "freezing": -0.07,
            "rain": -0.08, "snow": -0.14, "windy": -0.12,
        },
    },
    "RB": {
        # P3 combines rushing and receiving into one RB team-yardage bucket;
        # applying it to player rushing yards is a proxy, not an exact split.
        "rushing_yards": {
            "indoor": 0.02, "hot": -0.02, "freezing": 0.03,
            "rain": 0.03, "snow": 0.10, "windy": 0.00,
        },
        "receptions": {
            "indoor": 0.05, "hot": 0.02, "freezing": -0.03,
            "rain": -0.05, "snow": -0.12, "windy": -0.04,
        },
    },
}

ALIASES = {
    "player_pass_yds": "passing_yards",
    "player_rec_yds": "receiving_yards",
    "player_receptions": "receptions",
}


def number(value):
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def classify_weather(game):
    """Return observed weather categories when schedule data supports them."""
    roof = str(game.get("roof") or "").strip().lower()
    if any(token in roof for token in ("dome", "closed", "indoor")):
        return {"indoor"}

    categories = set()
    conditions = str(
        game.get("game_weather") or game.get("weather") or game.get("conditions") or ""
    ).lower()
    if re.search(r"\b(rain|rainy|shower|drizzle|thunderstorm|storm)\b", conditions):
        categories.add("rain")
    if re.search(r"\b(snow|snowy|sleet|blizzard)\b", conditions):
        categories.add("snow")

    wind = number(game.get("wind"))
    temp = number(game.get("temp"))
    if wind is not None and wind >= 15:
        categories.add("windy")
    if temp is not None:
        if temp < 32:
            categories.add("freezing")
        elif temp < 45:
            categories.add("cold")
        elif temp < 60:
            categories.add("cool")
        elif temp < 75:
            categories.add("mild")
        elif temp < 85:
            categories.add("warm")
        else:
            categories.add("hot")
    return categories


def candidate_projection(baseline, position, market, categories):
    """Apply the strongest available P3 split once, matching the live candidate."""
    metric = ALIASES.get(str(market or "").lower(), str(market or "").lower())
    by_category = RATES.get(str(position or "").upper(), {}).get(metric, {})
    applicable = [
        (category, rate)
        for category, rate in by_category.items()
        if category in categories and rate != 0
    ]
    if not applicable:
        return baseline, None
    category, rate = max(applicable, key=lambda item: abs(item[1]))
    return max(0.0, baseline * (1 + rate * SHRINKAGE)), category


def team_pair(game):
    home = str(game.get("home_team") or game.get("home") or "").upper()
    away = str(game.get("away_team") or game.get("away") or "").upper()
    return home, away


def player_positions(seasons):
    positions = {}
    for season in seasons:
        rows = nfl.load_player_stats([season], summary_level="week").to_dicts()
        for row in rows:
            try:
                key = (
                    int(row["season"]), int(row["week"]),
                    str(row.get("player_id") or ""),
                    str(row.get("team") or "").upper(),
                )
            except (KeyError, TypeError, ValueError):
                continue
            position = str(row.get("position") or "").upper()
            if position:
                positions[key] = position
    return positions


def summarize(rows, position_map, weather_map):
    paired = []
    by_group = defaultdict(list)
    by_season = defaultdict(list)
    exposure = Counter()
    joined = 0

    for row in rows:
        try:
            season, week = int(row["season"]), int(row["week"])
            team, opponent = str(row["team"]).upper(), str(row["opponent"]).upper()
            player_id = str(row["player_id"])
            market = str(row["market"]).lower()
            baseline, actual = float(row["new"]), float(row["actual"])
        except (KeyError, TypeError, ValueError):
            continue

        position = position_map.get((season, week, player_id, team))
        game = weather_map.get((season, week, team, opponent))
        if not position or game is None:
            continue
        joined += 1
        categories = classify_weather(game)
        adjusted, selected = candidate_projection(baseline, position, market, categories)
        record = {
            "season": season, "week": week, "position": position,
            "market": market, "actual": actual, "baseline": baseline,
            "candidate": adjusted, "categories": sorted(categories),
            "selected_category": selected,
        }
        paired.append(record)
        by_season[season].append(record)
        if selected:
            exposure[selected] += 1
            by_group[(position, market, selected)].append(record)

    def metrics(subset):
        if not subset:
            return {"samples": 0, "baseline_mae": None, "candidate_mae": None,
                    "baseline_rmse": None, "candidate_rmse": None,
                    "mae_improvement_pct": None}
        base_errors = [(r["baseline"] - r["actual"]) for r in subset]
        candidate_errors = [(r["candidate"] - r["actual"]) for r in subset]
        base_mae = sum(abs(error) for error in base_errors) / len(subset)
        candidate_mae = sum(abs(error) for error in candidate_errors) / len(subset)
        base_rmse = math.sqrt(sum(error * error for error in base_errors) / len(subset))
        candidate_rmse = math.sqrt(sum(error * error for error in candidate_errors) / len(subset))
        return {
            "samples": len(subset),
            "baseline_mae": round(base_mae, 3),
            "candidate_mae": round(candidate_mae, 3),
            "baseline_rmse": round(base_rmse, 3),
            "candidate_rmse": round(candidate_rmse, 3),
            "mae_improvement_pct": round((base_mae - candidate_mae) / base_mae * 100, 2)
            if base_mae else None,
        }

    groups = [
        {"position": key[0], "market": key[1], "weather": key[2], **metrics(group)}
        for key, group in sorted(by_group.items())
    ]
    seasons = {str(year): metrics(group) for year, group in sorted(by_season.items())}
    adjusted_rows = [r for r in paired if r["selected_category"]]
    return {
        "method": (
            "Same historical player-game rows; existing walk-forward baseline versus "
            "baseline adjusted by the strongest matching P3 position/weather split, "
            "50% shrinkage. Weather labels come from observed game conditions."
        ),
        "status": "SCREENING_ONLY_OBSERVED_WEATHER_NOT_PREGAME_FORECAST",
        "seasons_requested": sorted({int(r["season"]) for r in rows if r.get("season") is not None}),
        "matched_weather_rows": joined,
        "paired_forecasts": len(paired),
        "weather_adjusted_forecasts": len(adjusted_rows),
        "weather_adjustment_coverage_pct": round(100 * len(adjusted_rows) / len(paired), 2) if paired else 0,
        "weather_categories_selected": dict(sorted(exposure.items())),
        "all_matched": metrics(paired),
        "weather_adjusted_only": metrics(adjusted_rows),
        "by_season": seasons,
        "by_position_market_weather": groups,
        "promotion_eligible": False,
        "promotion_note": (
            "Observed game weather is not a historical pregame forecast. This replay "
            "screens the P3 adjustment but cannot alone justify a live promotion."
        ),
    }


def build_weather_map(seasons):
    games = nfl.load_schedules(seasons).to_dicts()
    result = {}
    for game in games:
        try:
            season = int(game["season"])
            week = int(game["week"])
        except (KeyError, TypeError, ValueError):
            continue
        home, away = team_pair(game)
        if not home or not away:
            continue
        result[(season, week, home, away)] = game
        result[(season, week, away, home)] = game
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=2016)
    parser.add_argument("--end", type=int, default=2025)
    parser.add_argument("--output-dir", type=Path, default=Path("research/weather-player-results"))
    args = parser.parse_args()
    if args.start < 2016 or args.end < args.start or args.end > 2026:
        parser.error("Use a valid completed-season range from 2016 through 2025")
    seasons = tuple(range(args.start, args.end + 1))
    baseline_rows = backtest(seasons)
    if not baseline_rows:
        raise RuntimeError("No historical baseline predictions were generated")
    positions = player_positions(seasons)
    weather = build_weather_map(list(seasons))
    report = summarize(baseline_rows, positions, weather)
    if report["paired_forecasts"] == 0:
        raise RuntimeError("No forecasts joined to historical position and weather records")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "weather-player-backtest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Historical player weather adjustment replay",
        "",
        f"Status: {report['status']}",
        f"Seasons: {args.start}–{args.end}",
        f"Matched player forecasts: {report['paired_forecasts']}",
        f"Forecasts with a weather adjustment: {report['weather_adjusted_forecasts']} "
        f"({report['weather_adjustment_coverage_pct']}%)",
        "",
        "## Same matched player-game forecasts",
        "",
        "| Samples | Baseline MAE | Weather MAE | Baseline RMSE | Weather RMSE | MAE change |",
        "|---:|---:|---:|---:|---:|---:|",
        "| {samples} | {baseline_mae} | {candidate_mae} | {baseline_rmse} | "
        "{candidate_rmse} | {mae_improvement_pct}% |".format(**report["all_matched"]),
        "",
        "## By season",
        "",
        "| Season | N | Baseline MAE | Weather MAE | MAE change |",
        "|---:|---:|---:|---:|---:|",
    ]
    for season, values in report["by_season"].items():
        lines.append(
            f"| {season} | {values['samples']} | {values['baseline_mae']} | "
            f"{values['candidate_mae']} | {values['mae_improvement_pct']}% |"
        )
    lines.extend([
        "",
        "Research screen only: this uses observed game weather, not archived pregame forecasts. "
        "It cannot trigger a production promotion.",
    ])
    (args.output_dir / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
