#!/usr/bin/env python3
"""Research-only pregame score projections using past nflverse results.

Uses no bookmaker lines and cannot write public dashboard files.
"""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from build_team_baseline import build, load_games

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--schedule-csv", type=Path, required=True)
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--week", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if not 2 <= a.week <= 18:
        p.error("Regular season week must be 2..18 (week 1 needs prior-season model)")
    if a.output.resolve().is_relative_to((Path(__file__).resolve().parents[1]/"data").resolve()):
        p.error("Research script cannot overwrite public data/")
    past = load_games(a.schedule_csv, a.season, a.week)
    if not past:
        p.error("No completed prior-week results available")
    base = build(past)
    teams = base["teams"]
    upcoming = []
    with a.schedule_csv.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                if int(row["season"]) != a.season or int(row["week"]) != a.week or row.get("game_type","REG") != "REG":
                    continue
            except (ValueError, KeyError):
                continue
            home, away = row.get("home_team"), row.get("away_team")
            if not home or not away or home == away:
                continue
            if home not in teams or away not in teams or not teams[home]["eligible"] or not teams[away]["eligible"]:
                continue
            # Historical average home advantage is deliberately NOT estimated
            # from current-week data; conservative constant until backtested.
            h = 0.5*(teams[home]["points_for"] + teams[away]["points_against"]) + 1.0
            v = 0.5*(teams[away]["points_for"] + teams[home]["points_against"]) - 1.0
            h, v = round(max(0, h), 2), round(max(0, v), 2)
            upcoming.append({"game_id":row.get("game_id") or f"{a.season}_{a.week:02}_{away}_{home}",
                "home":home,"away":away,"projected_home_score":h,"projected_away_score":v,
                "projected_margin_home":round(h-v,2),"projected_total":round(h+v,2),
                "method":"shrunk_points_baseline_research_only"})
    if not upcoming:
        p.error("No upcoming matchups with eligible team history; refusing empty output")
    output={"season":a.season,"week":a.week,"generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "source":"nflverse_schedule_csv","status":"research_only_uncalibrated",
        "training_games":len(past),"games":upcoming}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")
    print(f"Generated {len(upcoming)} research game projections; NOT published")
if __name__=="__main__":
    main()
