#!/usr/bin/env python3
"""Immutable pre-kickoff snapshots and strictly observed weekly accuracy. Research only."""
import argparse,csv,json,math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

MARKETS=("passing_yards","rushing_yards","receiving_yards")
def kickoff(row):
    try:
        return datetime.fromisoformat(row["gameday"]+"T"+row["gametime"]).replace(tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)
    except (KeyError,TypeError,ValueError):return None

def metrics(errors):
    n=len(errors)
    return {"samples":n,"mae":round(sum(map(abs,errors))/n,2),"rmse":round(math.sqrt(sum(e*e for e in errors)/n),2),"bias":round(sum(errors)/n,2)} if n else {"samples":0,"mae":None,"rmse":None,"bias":None}

def snapshot(games,players,schedule,now):
    if (games["season"],games["week"])!=(players["season"],players["week"]):raise ValueError("Season/week mismatch")
    matches={(r["home_team"],r["away_team"]):r for r in schedule if r.get("season")==str(games["season"]) and r.get("week")==str(games["week"]) and r.get("game_type","REG")=="REG"}
    included=[]
    for game in games.get("games",[]):
        match=matches.get((game["home"],game["away"]))
        if not match or not kickoff(match) or kickoff(match)<=now:continue
        included.append({**game,"kickoff_utc":kickoff(match).isoformat()})
    ids={g["game_id"] for g in included}
    projected=[p for p in players.get("projections",[]) if p.get("game_id") in ids]
    if not included:raise ValueError("No future games; refusing retroactive pregame snapshot")
    return {"status":"locked_pregame_research","season":games["season"],"week":games["week"],"locked_at_utc":now.isoformat(),"games":included,"players":projected,"note":"First snapshot is immutable; no late-run replacement or post-kickoff backfill."}

def grade(archive,schedule,stats,now):
    schedule_by_id={r.get("game_id"):r for r in schedule}
    actual=defaultdict(list)
    for row in stats:
        try:
            if int(row["season"])!=archive["season"] or int(row["week"])!=archive["week"] or row.get("season_type","REG")!="REG":continue
            pid=row.get("player_id") or row.get("gsis_id")
            for market in MARKETS:
                value=float(row[market])
                if pid and math.isfinite(value) and 0<=value<=700:actual[(pid,market)].append(value)
        except (KeyError,ValueError,TypeError):continue
    errors=defaultdict(list);game_errors=defaultdict(list);counts=defaultdict(int)
    completed=set()
    for g in archive["games"]:
        r=schedule_by_id.get(g["game_id"])
        if not r or not kickoff(r) or kickoff(r)>now:continue
        try:
            home=float(r["home_score"]);away=float(r["away_score"])
            if not all(map(math.isfinite,(home,away))):continue
        except (KeyError,TypeError,ValueError):continue
        completed.add(g["game_id"])
        game_errors["home_margin"].append(float(g["projected_margin_home"])-(home-away))
        game_errors["total"].append(float(g["projected_total"])-(home+away))
        for key,actual_value in (("spread_line",home-away),("total_line",home+away)):
            try:
                line=float(r[key])
                if not math.isfinite(line):continue
                if key=="spread_line":
                    # nflverse spread_line convention is home-favorite negative/positive may vary;
                    # do not infer ATS outcome without verified line convention.
                    counts["spread_lines_present_not_graded"]+=1
                else:
                    counts["total_lines_present"]+=1
                    if home+away!=line:counts["total_side_correct" if (float(g["projected_total"])-line)*(home+away-line)>0 else "total_side_incorrect"]+=1
            except (ValueError,TypeError,KeyError):pass
    for p in archive["players"]:
        if p.get("game_id") not in completed:continue
        observed=actual.get((p.get("player_id"),p.get("market")),[])
        if len(observed)==1:errors[p["market"]].append(float(p["projected_yards"])-observed[0])
    return {"season":archive["season"],"week":archive["week"],"locked_at_utc":archive["locked_at_utc"],
            "status":"graded_observed_only" if completed else "awaiting_completed_games",
            "completed_games":len(completed),"game_metrics":{k:metrics(v) for k,v in game_errors.items()},
            "player_metrics":{m:metrics(errors[m]) for m in MARKETS},"market_diagnostics":dict(counts),
            "note":"Only timestamped pre-kickoff snapshots are graded. Missing players/lines are not counted as misses. ATS omitted until sportsbook line sign and timestamp are verified."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--schedule-csv",type=Path,required=True)
    p.add_argument("--stats-csv",type=Path,required=True)
    p.add_argument("--games-json",type=Path,required=True)
    p.add_argument("--players-json",type=Path,required=True)
    p.add_argument("--archive-dir",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args();now=datetime.now(timezone.utc)
    with a.schedule_csv.open(newline="",encoding="utf-8-sig") as f:schedule=list(csv.DictReader(f))
    with a.stats_csv.open(newline="",encoding="utf-8-sig") as f:stats=list(csv.DictReader(f))
    games=json.loads(a.games_json.read_text());players=json.loads(a.players_json.read_text())
    a.archive_dir.mkdir(parents=True,exist_ok=True)
    target=a.archive_dir/(str(games["season"])+"-week-"+str(games["week"])+".json")
    if not target.exists():
        try:
            record=snapshot(games,players,schedule,now)
            with target.open("x") as f:json.dump(record,f,indent=2)
            print("Locked immutable pregame snapshot:",target)
        except ValueError as exc:print("Snapshot skipped:",exc)
    reports=[]
    for path in sorted(a.archive_dir.glob("*.json")):
        record=json.loads(path.read_text())
        if record.get("status")!="locked_pregame_research":continue
        reports.append(grade(record,schedule,stats,now))
    aggregate=defaultdict(list)
    for report in reports:
        for category in ("player_metrics","game_metrics"):
            for market,m in report[category].items():
                if m["samples"]:aggregate[(category,market)].append(m)
    season_totals={}
    for (category,market),groups in aggregate.items():
        n=sum(x["samples"] for x in groups)
        season_totals.setdefault(category,{})[market]={"samples":n,"mae":round(sum(x["mae"]*x["samples"] for x in groups)/n,2),
          "rmse":round(math.sqrt(sum(x["rmse"]**2*x["samples"] for x in groups)/n),2)}
    output={"status":"timestamped_pregame_accuracy_only","generated_at_utc":now.isoformat(),
      "graded_weeks":sum(r["completed_games"]>0 for r in reports),"weekly_reports":reports,
      "season_to_date":season_totals,"note":"Aggregated errors are rounded from weekly metrics. No historical backfill is treated as a locked pregame prediction."}
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(output,indent=2)+"\n")
    print("Weekly model performance:",{"snapshots":len(reports),"graded_weeks":output["graded_weeks"]})
if __name__=="__main__":main()
