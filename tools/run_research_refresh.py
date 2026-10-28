#!/usr/bin/env python3
"""Orchestrate read-only research forecasts from downloaded free NFL CSV files."""
import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def season_week(path, requested_season, requested_week):
    now = datetime.now(timezone.utc)
    # Explicit input takes precedence; scheduled run uses next unplayed regular-season
    # game in the provided schedule. No game may be assumed future if kickoff missing.
    if requested_season and requested_week:
        return int(requested_season), int(requested_week)
    candidates=[]
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                kickoff=datetime.fromisoformat(row["gameday"]+"T"+row["gametime"]+":00-04:00")
                # NFL local timezone DST conversion handled below with zoneinfo.
                from zoneinfo import ZoneInfo
                kickoff=datetime.fromisoformat(row["gameday"]+"T"+row["gametime"]).replace(tzinfo=ZoneInfo("America/New_York"))
                season,week=int(row["season"]),int(row["week"])
            except (ValueError,TypeError,KeyError):
                continue
            if row.get("game_type","REG")!="REG" or kickoff.astimezone(timezone.utc)<=now:
                continue
            candidates.append((kickoff,season,week))
    if not candidates:
        raise ValueError("No future regular-season games with valid kickoff timestamps")
    _,season,week=min(candidates)
    return season,week

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--schedule-csv",type=Path,required=True)
    p.add_argument("--weekly-csv",type=Path,required=True)
    p.add_argument("--season",default="")
    p.add_argument("--week",default="")
    p.add_argument("--output-dir",type=Path,required=True)
    a=p.parse_args()
    if bool(a.season)!=bool(a.week):
        p.error("Specify both season and week or neither")
    season,week=season_week(a.schedule_csv,a.season,a.week)
    a.output_dir.mkdir(parents=True,exist_ok=True)
    summary={"season":season,"week":week,"status":"research_only_no_publication","steps":{}}
    diagnostic=subprocess.run([sys.executable,str(ROOT/"tools/diagnose_player_feed.py"),
        "--csv",str(a.weekly_csv),"--season",str(season),"--week",str(week)],
        capture_output=True,text=True,timeout=120,check=False)
    summary["player_feed_diagnostic"]={"exit_code":diagnostic.returncode,
        "stdout":diagnostic.stdout[-10000:],"stderr":diagnostic.stderr[-2000:]}
    (a.output_dir/"player-feed-diagnostic.json").write_text(diagnostic.stdout or "{}")
    commands={
      "games":[sys.executable,str(ROOT/"tools/project_game_scores.py"),
               "--schedule-csv",str(a.schedule_csv),"--season",str(season),
               "--week",str(week),"--output",str(a.output_dir/"game-projections.json")],
      "players":[sys.executable,str(ROOT/"tools/project_player_yards.py"),
                 "--weekly-csv",str(a.weekly_csv),"--season",str(season),
                 "--week",str(week),"--output",str(a.output_dir/"player-projections.json")],
      "player_backtest":[sys.executable,str(ROOT/"tools/backtest_player_yards.py"),
                         "--weekly-csv",str(a.weekly_csv),"--season",str(season),
                         "--first-week","5","--last-week",str(min(18,max(5,week-1)))]
    }
    for label,cmd in commands.items():
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=120,check=False)
        summary["steps"][label]={"exit_code":result.returncode,"stdout":result.stdout[-6000:],
                                  "stderr":result.stderr[-2000:]}
        if label=="player_backtest" and result.returncode==0:
            (a.output_dir/"player-backtest.json").write_text(result.stdout)
    (a.output_dir/"run-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    if summary["steps"]["player_backtest"]["exit_code"] == 0:
        try:
            report = json.loads(summary["steps"]["player_backtest"]["stdout"])
            if not report.get("markets"):
                summary["steps"]["player_backtest"]["exit_code"] = 3
                summary["steps"]["player_backtest"]["stderr"] = "No graded player observations; cannot claim a successful backtest"
        except (ValueError, TypeError):
            summary["steps"]["player_backtest"]["exit_code"] = 3
            summary["steps"]["player_backtest"]["stderr"] = "Unparseable backtest output"
    (a.output_dir/"run-summary.json").write_text(json.dumps(summary,indent=2)+"\\n")
    if diagnostic.returncode or any(x["exit_code"] for x in summary["steps"].values()):
        print(json.dumps(summary,indent=2))
        raise SystemExit("One or more research steps failed; no publication attempted")
    print(json.dumps({"season":season,"week":week,"research_completed":True,
                      "public_dashboard_updated":False}))
if __name__=="__main__":
    main()
