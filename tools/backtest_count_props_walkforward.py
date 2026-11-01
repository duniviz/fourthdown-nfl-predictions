#!/usr/bin/env python3
"""Research-only walk-forward count props: QB completions, RB rush attempts, WR receptions.
No sportsbook edges, calibrated probabilities, or production publication.
"""
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

MARKETS = {
    "qb_completions": ("QB", "completions", "attempts"),
    "rb_rush_attempts": ("RB", "carries", None),
    "wr_receptions": ("WR", "receptions", "targets"),
}
ALIASES = {"QB": {"QB"}, "RB": {"RB"}, "WR": {"WR"}}

def number(row, field):
    try:
        v = float(row.get(field, ""))
        return v if math.isfinite(v) and v >= 0 else None
    except (ValueError, TypeError):
        return None

def read_games(rows):
    games = defaultdict(dict)
    for row in rows:
        try:
            season, week = int(row["season"]), int(row["week"])
        except (KeyError, ValueError, TypeError):
            continue
        if row.get("season_type", "REG") != "REG" or not 1 <= week <= 18:
            continue
        pid = row.get("player_id") or row.get("gsis_id")
        pos = str(row.get("position", "")).upper()
        if not pid or pos not in ALIASES:
            continue
        key = (season, week, pid)
        if key in games:
            continue  # one player-week record only; avoid double-counting
        games[key] = dict(row)
    return games

def predict(history, market, variant):
    position, outcome, opportunities = MARKETS[market]
    eligible = [r for r in history if str(r.get("position", "")).upper() == position]
    if len(eligible) < 3:
        return None
    eligible = sorted(eligible, key=lambda r: int(r["week"]))
    values = [number(r, outcome) for r in eligible]
    if any(v is None for v in values):
        return None
    recent = values[-5:]
    baseline = sum(recent) / len(recent)
    if variant == "baseline" or not opportunities:
        return baseline if variant == "baseline" else .65 * baseline + .35 * sum(values) / len(values)
    pairs = [(number(r, opportunities), number(r, outcome)) for r in eligible]
    if any(a is None or b is None for a, b in pairs):
        return None
    recent_pairs = pairs[-5:]
    opp = .65 * sum(a for a, _ in recent_pairs) / len(recent_pairs) + .35 * sum(a for a, _ in pairs) / len(pairs)
    attempts = sum(a for a, _ in pairs)
    rate = (sum(b for _, b in recent_pairs) + sum(b for _, b in pairs)) / (sum(a for a, _ in recent_pairs) + attempts) if attempts else 0
    return max(0, min(opp, opp * rate))

def evaluate(rows, seasons, through_week=18):
    games = read_games(rows)
    by_player = defaultdict(list)
    for (season, week, pid), row in games.items():
        by_player[(season, pid)].append(row)
    errors = defaultdict(list)
    weekly = defaultdict(lambda: defaultdict(int))
    for (season, pid), player_rows in by_player.items():
        if season not in seasons:
            continue
        player_rows.sort(key=lambda r: int(r["week"]))
        for current in player_rows:
            week = int(current["week"])
            if week > through_week:
                continue
            history = [r for r in player_rows if int(r["week"]) < week]
            for market, (pos, field, _) in MARKETS.items():
                if current.get("position", "").upper() != pos:
                    continue
                actual = number(current, field)
                if actual is None:
                    continue
                for variant in ("baseline", "candidate"):
                    estimate = predict(history, market, variant)
                    if estimate is None:
                        continue
                    errors[(market, variant)].append(estimate - actual)
                    weekly[str(season) + "-W" + str(week)][market] += int(variant == "candidate")
    summary = {}
    for market in MARKETS:
        summary[market] = {}
        for variant in ("baseline", "candidate"):
            e = errors[(market, variant)]
            n = len(e)
            summary[market][variant] = {"samples": n, "mae": round(sum(map(abs, e))/n, 3) if n else None,
                "rmse": round(math.sqrt(sum(x*x for x in e)/n), 3) if n else None,
                "bias": round(sum(e)/n, 3) if n else None}
        a, b = summary[market]["baseline"], summary[market]["candidate"]
        summary[market]["candidate_beats_baseline"] = bool(a["samples"] and a["samples"] == b["samples"] and b["mae"] < a["mae"] and b["rmse"] < a["rmse"])
    return {"status": "research_only", "seasons": sorted(seasons), "through_week": through_week,
        "markets": summary, "weekly_candidate_samples": dict(weekly),
        "limitations": "Historical observed-player evaluation; does not model active-roster selection, opponent position defense, DK odds, uncertainty or betting returns. No live publication."}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekly-csv", type=Path, required=True)
    parser.add_argument("--seasons", nargs="+", type=int, default=[2024, 2025, 2026])
    parser.add_argument("--through-week", type=int, default=18)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.weekly_csv.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    result = evaluate(rows, set(args.seasons), args.through_week)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["markets"], indent=2))

if __name__ == "__main__":
    main()
