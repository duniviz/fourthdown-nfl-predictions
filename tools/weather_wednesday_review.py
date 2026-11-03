#!/usr/bin/env python3
"""Wednesday weather v1 comparison. Only grade verified frozen pregame records."""
import datetime as dt
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
def load(name):
    try:return json.loads((DATA/name).read_text())
    except (OSError,ValueError):return {}
def utc(value):
    try:
        d=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return d if d.tzinfo else None
    except (TypeError,ValueError):return None
def compare(snapshots,results):
    outcomes={(str(r.get("game_id")),str(r.get("player_id")),str(r.get("stat_key") or r.get("market"))):r
              for r in results if r.get("actual") is not None}
    aliases={"player_pass_yds":"passing_yards","player_rush_yds":"rushing_yards",
             "player_rec_yds":"receiving_yards","player_pass_completions":"pass_completions",
             "player_pass_attempts":"pass_attempts","player_rush_attempts":"rush_attempts",
             "player_receptions":"receptions"}
    by_market={}
    for row in snapshots:
        captured,kickoff=utc(row.get("captured_at")),utc(row.get("kickoff"))
        if not captured or not kickoff or captured>=kickoff:continue
        if row.get("weather_version")!="weather-template-v1" or row.get("weather_projection") is None:continue
        market=aliases.get(row.get("market"),row.get("market"))
        result=outcomes.get((str(row.get("game_id")),str(row.get("player_id")),market))
        if not result:continue
        try:
            actual=float(result["actual"]);base=float(row["projection"]);wx=float(row["weather_projection"])
        except (TypeError,ValueError,KeyError):continue
        if min(actual,base,wx)<0:continue
        item=by_market.setdefault(market,{"samples":0,"baseline_absolute_error":0,"weather_absolute_error":0})
        item["samples"]+=1
        item["baseline_absolute_error"]+=abs(actual-base)
        item["weather_absolute_error"]+=abs(actual-wx)
    report={}
    for market,item in sorted(by_market.items()):
        n=item["samples"]
        baseline=item["baseline_absolute_error"]/n
        weather=item["weather_absolute_error"]/n
        report[market]={"samples":n,"baseline_mae":round(baseline,3),"weather_mae":round(weather,3),
                        "mae_improvement":round(baseline-weather,3),"sufficient_for_review":n>=30}
    return {"generated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "version":"weather-template-v1","research_only":True,"production_changed":False,
            "automatic_promotion":False,"minimum_market_samples":30,
            "markets":report,"status":"comparison_available" if report else "awaiting_frozen_weather_and_verified_outcomes",
            "note":"Same-game comparison only; descriptive, not an independent historical holdout. No automatic weight changes."}
def main():
    result=compare(load("pregame-snapshots.json").get("records",[]),load("player-results.json").get("rows",[]))
    (DATA/"weather-wednesday-review.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
