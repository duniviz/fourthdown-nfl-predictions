#!/usr/bin/env python3
"""Research-only, fail-closed matching of player forecasts to DraftKings odds."""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

MARKETS={"passing_yards":{"player_pass_yds","player_passing_yards"},
         "rushing_yards":{"player_rush_yds","player_rushing_yards"},
         "receiving_yards":{"player_rec_yds","player_receiving_yards"}}
TEAMS={"ARI":"Arizona Cardinals","ATL":"Atlanta Falcons","BAL":"Baltimore Ravens","BUF":"Buffalo Bills","CAR":"Carolina Panthers","CHI":"Chicago Bears","CIN":"Cincinnati Bengals","CLE":"Cleveland Browns","DAL":"Dallas Cowboys","DEN":"Denver Broncos","DET":"Detroit Lions","GB":"Green Bay Packers","HOU":"Houston Texans","IND":"Indianapolis Colts","JAC":"Jacksonville Jaguars","JAX":"Jacksonville Jaguars","KC":"Kansas City Chiefs","LV":"Las Vegas Raiders","LAC":"Los Angeles Chargers","LA":"Los Angeles Rams","MIA":"Miami Dolphins","MIN":"Minnesota Vikings","NE":"New England Patriots","NO":"New Orleans Saints","NYG":"New York Giants","NYJ":"New York Jets","PHI":"Philadelphia Eagles","PIT":"Pittsburgh Steelers","SF":"San Francisco 49ers","SEA":"Seattle Seahawks","TB":"Tampa Bay Buccaneers","TEN":"Tennessee Titans","WAS":"Washington Commanders"}
def norm(x):
    return re.sub(r"[^a-z0-9]","",str(x or "").lower())
def team(x):
    return norm(TEAMS.get(str(x or "").upper(),x))
def timestamp(x):
    try:
        return datetime.fromisoformat(str(x).replace("Z","+00:00")).astimezone(timezone.utc)
    except (ValueError,TypeError):
        return None
def match(players,odds,now,max_age_hours=3):
    rows=odds.get("rows",[])
    if odds.get("bookmaker","").lower()!="draftkings":
        raise ValueError("Odds must explicitly identify DraftKings")
    matched=[]
    counts={"total":len(players),"matched":0,"missing":0,"stale":0,"ambiguous":0,"unverified":0}
    for p in players:
        candidates=[]
        stale=False
        for q in rows:
            if q.get("market_key") not in MARKETS.get(p.get("market"),set()): continue
            if norm(q.get("player"))!=norm(p.get("player_name")): continue
            if {team(q.get("home_team")),team(q.get("away_team"))}!={team(p.get("team")),team(p.get("opponent"))}: continue
            try:
                line=float(q["line"])
            except (TypeError,ValueError,KeyError):
                continue
            if not 0<line<700: continue
            t=timestamp(q.get("last_update"))
            if t is None or not 0<=(now-t).total_seconds()<=max_age_hours*3600:
                stale=True
                continue
            candidates.append((line,t,q))
        unique={line for line,_,_ in candidates}
        entry={"player_id":p.get("player_id"),"player_name":p.get("player_name"),"team":p.get("team"),"opponent":p.get("opponent"),"market":p.get("market"),"projected_yards":p.get("projected_yards"),"availability_status":p.get("availability_status","unverified"),"recommendation_eligible":bool(p.get("eligible_for_recommendation",False))}
        if len(unique)==1:
            line=next(iter(unique))
            q=max((x for x in candidates if x[0]==line),key=lambda x:x[1])[2]
            entry.update({"match_status":"matched","dk_line":line,"difference_yards":round(float(p["projected_yards"])-line,1),"over_price":q.get("over_price"),"under_price":q.get("under_price"),"last_update":q.get("last_update")})
            counts["matched"]+=1
        else:
            reason="ambiguous" if len(unique)>1 else ("stale" if stale else "missing")
            entry.update({"match_status":reason,"dk_line":None,"difference_yards":None})
            counts[reason]+=1
        if not entry["recommendation_eligible"]: counts["unverified"]+=1
        matched.append(entry)
    return matched,counts
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--players-json",type=Path,required=True)
    p.add_argument("--odds-json",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--max-age-hours",type=float,default=3)
    a=p.parse_args()
    if a.max_age_hours<=0: p.error("max-age-hours must be positive")
    with a.players_json.open() as f: players=json.load(f)
    with a.odds_json.open() as f: odds=json.load(f)
    now=datetime.now(timezone.utc)
    matches,counts=match(players.get("projections",[]),odds,now,a.max_age_hours)
    result={"season":players.get("season"),"week":players.get("week"),"generated_at_utc":now.isoformat(),"status":"research_only_no_publication","source":"DraftKings via existing ParlayAPI snapshot","odds_snapshot_generated_at":odds.get("generated_at_utc"),"counts":counts,"note":"Differences are not calibrated edges; stale, ambiguous, missing or unverified players are not betting recommendations","comparisons":matches}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(counts))
if __name__=="__main__": main()
