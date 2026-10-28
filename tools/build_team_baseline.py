#!/usr/bin/env python3
"""Build reproducible, research-only team scoring baselines from free nflverse CSV.

Input must be an explicitly supplied local CSV snapshot; never downloads
unverified live data, changes published forecasts, or fabricates player stats.
"""
import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

def load_games(path, season, through_week):
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                if int(r.get("season", -1)) != season or int(r.get("week", -1)) >= through_week:
                    continue
                hs, aw = float(r["home_score"]), float(r["away_score"])
            except (ValueError, TypeError, KeyError):
                continue
            if r.get("game_type", "REG") != "REG" or not r.get("home_team") or not r.get("away_team"):
                continue
            if hs < 0 or aw < 0:
                continue
            rows.append((int(r["week"]), r["home_team"], r["away_team"], hs, aw))
    return rows

def build(rows, min_games=3):
    totals = defaultdict(lambda: {"for": 0., "against": 0., "games": 0})
    for _, home, away, hs, aw in rows:
        for team, scored, allowed in ((home, hs, aw), (away, aw, hs)):
            x = totals[team]
            x["for"] += scored
            x["against"] += allowed
            x["games"] += 1
    league = sum(x["for"] for x in totals.values()) / max(1, sum(x["games"] for x in totals.values()))
    out = {}
    for team, x in sorted(totals.items()):
        n = x["games"]
        # Shrink small samples toward league average, without using future games.
        weight = n / (n + 5)
        out[team] = {"games": n, "points_for": round(weight*x["for"]/n+(1-weight)*league, 3),
                     "points_against": round(weight*x["against"]/n+(1-weight)*league, 3),
                     "eligible": n >= min_games}
    return {"league_points_per_team_game": round(league, 3), "teams": out}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--schedule-csv", type=Path, required=True)
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--through-week", type=int, required=True,
                   help="Exclusive cutoff; week N only uses completed weeks < N")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if not 1 <= a.through_week <= 23:
        p.error("through-week must be between 1 and 23")
    rows = load_games(a.schedule_csv, a.season, a.through_week)
    if not rows:
        p.error("No historical games found before cutoff; refusing to produce baseline")
    result = {"source": "supplied_nflverse_schedule_csv", "season": a.season,
              "through_week_exclusive": a.through_week, "games_used": len(rows),
              "generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "baseline": build(rows), "status": "research_only_not_production"}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2)+"\n")
    print(f"Wrote research baseline for {len(result['baseline']['teams'])} teams; not published")
if __name__ == "__main__":
    main()
