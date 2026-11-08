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
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from live.dk_identity import norm, team

def timestamp(x):
    try:
        return datetime.fromisoformat(str(x).replace("Z","+00:00")).astimezone(timezone.utc)
    except (ValueError,TypeError):
        return None
def match(players,odds,now,max_age_hours=3):
    rows=odds.get("rows",[])
    if odds.get("bookmaker","").lower()!="draftkings":
        raise ValueError("Odds must explicitly identify DraftKings")
    # Only accept abbreviated names if unique within the same matchup and market.
    def same_name(projection, quote):
        full=norm(projection)
        candidate=norm(quote)
        if full==candidate: return True
        parts=re.findall(r"[a-z]+",str(projection or "").lower())
        quoted=re.findall(r"[a-z]+",str(quote or "").lower())
        return len(parts)==2 and len(parts[0])==1 and len(quoted)>=2 and parts[0]==quoted[0][:1] and parts[1]==quoted[-1]
    def quote_could_belong_to(p, q):
        if q.get("market_key") not in MARKETS.get(p.get("market"),set()): return False
        if not same_name(p.get("player_name"),q.get("player")): return False
        if {team(q.get("home_team")),team(q.get("away_team"))}!={team(p.get("team")),team(p.get("opponent"))}: return False
        kickoff=timestamp(q.get("commence_time")) if q.get("commence_time") else None
        return not (kickoff and (now>=kickoff or (p.get("kickoff_utc") and kickoff!=timestamp(p["kickoff_utc"]))))
    # Inventory actual supported markets before claiming missing player lines.
    market_inventory={m:sum(q.get("market_key") in aliases for q in rows) for m,aliases in MARKETS.items()}
    unmatched_examples={m:[] for m in MARKETS}
    matched=[]
    counts={"total":len(players),"matched":0,"missing":0,"stale":0,"ambiguous":0,"unverified":0}
    for p in players:
        candidates=[]
        stale=False
        ambiguous_owner=False
        for q in rows:
            if not quote_could_belong_to(p,q): continue
            try:
                line=float(q["line"])
            except (TypeError,ValueError,KeyError):
                continue
            if not 0<line<700: continue
            t=timestamp(q.get("last_update"))
            if t is None or not 0<=(now-t).total_seconds()<=max_age_hours*3600:
                stale=True
                continue
            owners={(team(other.get("team")), norm(other.get("player_name")), str(other.get("player_id") or ""))
                    for other in players if quote_could_belong_to(other,q)}
            if len(owners)>1:
                ambiguous_owner=True
                continue
            candidates.append((line,t,q))
        unique={line for line,_,_ in candidates}
        # Never guess when an initial-and-surname match could refer to multiple names.
        candidate_names={norm(q.get("player")) for _,_,q in candidates}
        entry={"player_id":p.get("player_id"),"player_name":p.get("player_name"),"team":p.get("team"),"opponent":p.get("opponent"),"market":p.get("market"),"projected_yards":p.get("projected_yards"),"availability_status":p.get("availability_status","presumed_available"),"provisional_research_eligible":bool(p.get("provisional_research_eligible",False)),"recommendation_eligible":bool(p.get("eligible_for_recommendation",False))}
        if not ambiguous_owner and len(unique)==1 and len(candidate_names)==1:
            line=next(iter(unique))
            q=max((x for x in candidates if x[0]==line),key=lambda x:x[1])[2]
            entry.update({"match_status":"matched","dk_line":line,"difference_yards":round(float(p["projected_yards"])-line,1),"over_price":q.get("over_price"),"under_price":q.get("under_price"),"last_update":q.get("last_update")})
            counts["matched"]+=1
        else:
            reason="ambiguous" if ambiguous_owner or len(unique)>1 or len(candidate_names)>1 else ("stale" if stale else "missing")
            entry.update({"match_status":reason,"dk_line":None,"difference_yards":None})
            counts[reason]+=1
        if entry["match_status"]!="matched" and len(unmatched_examples.get(p.get("market"),[]))<10:
            unmatched_examples[p["market"]].append({"player":p.get("player_name"),"team":p.get("team"),"opponent":p.get("opponent"),"reason":entry["match_status"]})
        if not entry["recommendation_eligible"]: counts["unverified"]+=1
        matched.append(entry)
    return matched,counts,{"market_inventory":market_inventory,"unmatched_examples":unmatched_examples,"matched_pct":round(100*counts["matched"]/counts["total"],1) if counts["total"] else 0}
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
    matches,counts,coverage=match(players.get("projections",[]),odds,now,a.max_age_hours)
    result={"season":players.get("season"),"week":players.get("week"),"generated_at_utc":now.isoformat(),"status":"research_only_no_publication","source":"DraftKings via existing ParlayAPI snapshot","odds_snapshot_generated_at":odds.get("generated_at_utc"),"counts":counts,"coverage_diagnostics":coverage,"note":"Differences are not calibrated edges; stale, ambiguous, missing or unverified players are not betting recommendations","comparisons":matches}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(counts))
if __name__=="__main__": main()
