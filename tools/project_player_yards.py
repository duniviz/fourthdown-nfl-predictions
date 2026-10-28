#!/usr/bin/env python3
"""Research-only player yards projection from historical nflverse weekly data."""
import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

FIELDS={"passing_yards":"passing_yards","rushing_yards":"rushing_yards","receiving_yards":"receiving_yards"}
# Require meaningful historical involvement, not zero-yard placeholder rows.
ROLE_MIN={"passing_yards":10.0,"rushing_yards":5.0,"receiving_yards":5.0}
ROLE_ACTIVITY={"passing_yards":"attempts","rushing_yards":"carries","receiving_yards":"targets"}

def project(rows, season, week, min_games=3):
    history=defaultdict(lambda:defaultdict(list))
    activity=defaultdict(lambda:defaultdict(list))
    for r in rows:
        try:
            if int(r["season"]) != season or int(r["week"]) >= week or int(r["week"]) < 1:
                continue
            if r.get("season_type","REG") != "REG":
                continue
        except (KeyError, ValueError, TypeError):
            continue
        pid=r.get("player_id") or r.get("gsis_id")
        if not pid:
            continue
        for market, field in FIELDS.items():
            try:
                v=float(r[field])
            except (KeyError, ValueError, TypeError):
                continue
            if not (0 <= v <= 700):
                continue
            key=(pid,r.get("player_display_name") or r.get("player_name") or pid,r.get("recent_team") or r.get("team") or "")
            history[key][market].append((int(r["week"]),v))
            try:
                involvement=float(r.get(ROLE_ACTIVITY[market]) or 0)
            except (ValueError,TypeError):
                involvement=0
            activity[key][market].append((int(r["week"]),involvement))
    result=[]
    for (pid,name,team), markets in history.items():
        for market, vals in markets.items():
            vals.sort()
            if len(vals)<min_games:
                continue
            touches=sorted(activity[(pid,name,team)][market])
            recent_touches=touches[-5:]
            if sum(v for _,v in recent_touches)/len(recent_touches)<ROLE_MIN[market]:
                continue
            recent=vals[-5:]
            # Shrunk recent mean vs full season mean, no post-cutoff information.
            mean=sum(v for _,v in vals)/len(vals)
            recent_mean=sum(v for _,v in recent)/len(recent)
            estimate=round(.65*recent_mean+.35*mean,1)
            result.append({"player_id":pid,"player_name":name,"team":team,
                           "market":market,"projected_yards":estimate,
                           "games_used":len(vals),"latest_week_used":vals[-1][0],
                           "recent_opportunities":round(sum(v for _,v in recent_touches)/len(recent_touches),1)})
    return sorted(result,key=lambda x:(x["market"],x["player_name"],x["player_id"]))

def scheduled_opponents(path, season, week):
    matchups={}
    with path.open(newline="",encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            try:
                if int(row["season"])!=season or int(row["week"])!=week or row.get("game_type","REG")!="REG":
                    continue
            except (KeyError,ValueError,TypeError):
                continue
            home=row.get("home_team","").strip()
            away=row.get("away_team","").strip()
            if not home or not away or home==away or home in matchups or away in matchups:
                raise ValueError("Missing or conflicting scheduled teams")
            matchups[home]={"opponent":away,"home":True,"game_id":row.get("game_id","")}
            matchups[away]={"opponent":home,"home":False,"game_id":row.get("game_id","")}
    if not matchups:
        raise ValueError("No scheduled regular-season matchups found")
    return matchups

def opponent_defense(rows, season, week, min_games=3):
    """Historical yards allowed per opponent and market, strictly before target week."""
    allowed=defaultdict(lambda:defaultdict(lambda:defaultdict(float)))
    games=defaultdict(set)
    for r in rows:
        try:
            w=int(r["week"])
            if int(r["season"])!=season or w>=week or w<1 or r.get("season_type","REG")!="REG":
                continue
        except (KeyError,ValueError,TypeError):
            continue
        opponent=(r.get("opponent_team") or "").strip()
        team=(r.get("recent_team") or r.get("team") or "").strip()
        pid=r.get("player_id") or r.get("gsis_id")
        if not opponent or not team or not pid or opponent==team:
            continue
        game=(w,team)
        games[opponent].add(game)
        for market in FIELDS:
            try:
                yards=float(r[market])
            except (KeyError,ValueError,TypeError):
                continue
            if 0<=yards<=700:
                allowed[opponent][game][market]+=yards
    totals=defaultdict(lambda:defaultdict(list))
    for opponent, opponents_games in allowed.items():
        for game, markets in opponents_games.items():
            for market, yards in markets.items():
                totals[opponent][market].append(yards)
    # Compare defensive yards allowed to league mean, shrink aggressively
    # and cap adjustment. This is a descriptive signal, not a validated edge.
    league={}
    for market in FIELDS:
        values=[v for team in totals.values() for v in team.get(market,[]) if v>=0]
        if values:
            league[market]=sum(values)/len(values)
    factors={}
    for team, markets in totals.items():
        for market, values in markets.items():
            if len(values)<min_games or league.get(market,0)<=0:
                continue
            ratio=(sum(values)/len(values))/league[market]
            factors[(team,market)]=round(max(.9,min(1.1,1+.25*(ratio-1))),4)
    return factors

def injury_status(path, season, week):
    """Optional externally supplied pregame injury CSV: season,week,player_id,status."""
    statuses={}
    with path.open(newline="",encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            try:
                if int(row["season"])!=season or int(row["week"])!=week:
                    continue
            except (KeyError,ValueError,TypeError):
                continue
            pid=(row.get("player_id") or "").strip()
            status=(row.get("status") or "").strip().lower()
            if not pid or status not in {"out","doubtful","questionable","active","probable","inactive","ir","suspended"}:
                raise ValueError("Invalid injury row: player_id/status required and status must be recognized")
            if pid in statuses and statuses[pid]!=status:
                raise ValueError("Conflicting injury statuses for player "+pid)
            statuses[pid]=status
    return statuses

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--weekly-csv",type=Path,required=True)
    p.add_argument("--schedule-csv",type=Path,required=True)
    p.add_argument("--injury-csv",type=Path,default=None,help="Optional verified pregame availability CSV; no live feed is assumed")
    p.add_argument("--season",type=int,required=True)
    p.add_argument("--week",type=int,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if not 2<=a.week<=18:
        p.error("Week must be 2..18")
    if a.output.resolve().is_relative_to((Path(__file__).resolve().parents[1]/"data").resolve()):
        p.error("Research cannot overwrite published data")
    with a.weekly_csv.open(newline="",encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    result=project(rows,a.season,a.week)
    if not result:
        p.error("No eligible historical player samples")
    try:
        matchups=scheduled_opponents(a.schedule_csv,a.season,a.week)
    except ValueError as exc:
        p.error(str(exc))
    result=[{**item,**matchups[item["team"]]} for item in result if item["team"] in matchups]
    if not result:
        p.error("No role-eligible players matched the scheduled teams")
    defense=opponent_defense(rows,a.season,a.week)
    for item in result:
        factor=defense.get((item["opponent"],item["market"]),1.0)
        item["unadjusted_yards"]=item["projected_yards"]
        item["opponent_defense_factor"]=factor
        item["opponent_defense_available"]=(item["opponent"],item["market"]) in defense
        item["projected_yards"]=round(item["projected_yards"]*factor,1)
    statuses=injury_status(a.injury_csv,a.season,a.week) if a.injury_csv else {}
    excluded=0
    pre_filter_count=len(result)
    for item in result:
        status=statuses.get(item["player_id"],"presumed_available")
        item["availability_status"]=status
        item["availability_verified"]=status in {"active","probable"}
        item["eligible_for_recommendation"]=status in {"active","probable"}
        item["provisional_research_eligible"]=status=="presumed_available"
    if statuses:
        before=len(result)
        result=[item for item in result if item["availability_status"] not in {"out","inactive","doubtful","ir","suspended"}]
        excluded=before-len(result)
    from collections import Counter
    availability_counts=dict(sorted(Counter(x["availability_status"] for x in result).items()))
    matched_markets=sum(1 for x in result if x["availability_verified"])
    unique_players=len({x["player_id"] for x in result})
    verified_players=len({x["player_id"] for x in result if x["availability_verified"]})
    payload={"injury_diagnostics":{"feed_supplied":bool(a.injury_csv),"feed_status_records":len(statuses),"target_week_has_statuses":bool(statuses),"unique_projected_players":unique_players,"verified_projected_players":verified_players,"unverified_projected_players":unique_players-verified_players,"verification_coverage_pct":round(100*verified_players/unique_players,1) if unique_players else 0,"coverage_warning":"No verified current-week player availability; recommendations disabled" if not verified_players else "Partial coverage; only explicitly verified active/probable players eligible","projected_markets_before_exclusions":pre_filter_count,"matched_markets_before_exclusions":matched_markets+excluded,"matched_markets_remaining":matched_markets,"excluded_markets":excluded,"availability_counts":availability_counts,"eligible_markets":sum(x["eligible_for_recommendation"] for x in result)},"injury_source_supplied":bool(a.injury_csv),"injury_exclusions":excluded,"season":a.season,"week":a.week,"generated_at_utc":datetime.now(timezone.utc).isoformat(),
             "status":"research_only_uncalibrated","source":"supplied_nflverse_weekly_csv",
             "note":"Role- and schedule-filtered; conservative opponent-defense adjustment only when historical opponent field exists; availability is unverified without an explicitly supplied pregame injury file; no snap or sportsbook validation",
             "projections":result}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(payload,indent=2)+"\n")
    print(f"Wrote {len(result)} research player-market estimates, NOT published")
if __name__=="__main__":
    main()
