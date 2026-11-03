#!/usr/bin/env python3
"""Build strictly pregame opponent-vs-position yardage contexts from nflverse."""
import csv, io, json, os, urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SEASON=int(os.environ.get("NFL_SEASON",datetime.now(timezone.utc).year))
BASE="https://github.com/nflverse/nflverse-data/releases/download"
STATS=f"{BASE}/stats_player/stats_player_week_{SEASON}.csv"
SCHEDULE=f"{BASE}/schedules/games.csv"
MARKETS={"QB":"passing_yards","RB":"rushing_yards","WR":"receiving_yards","TE":"receiving_yards"}
ALIASES={"JAC":"JAX","LA":"LAR","STL":"LAR","SD":"LAC","OAK":"LV","WSH":"WAS"}
def team(s): return ALIASES.get(str(s or "").strip().upper(),str(s or "").strip().upper())
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"FOURTHDOWN-defensive-context/1.0"})
    with urllib.request.urlopen(req,timeout=90) as res: return list(csv.DictReader(io.StringIO(res.read().decode("utf-8-sig"))))
def number(v):
    try: return float(v or 0)
    except (TypeError,ValueError): return 0.0
def main():
    stats=fetch(STATS)
    schedules=fetch(SCHEDULE)
    # Only games with recorded final scores are eligible. Week boundaries are
    # intentionally conservative: a week's games cannot inform that same week.
    games=defaultdict(dict)
    for g in schedules:
        if str(g.get("season"))!=str(SEASON) or g.get("game_type",g.get("season_type","REG")) not in ("REG",""):
            continue
        try: week=int(g["week"])
        except (ValueError,KeyError): continue
        if not g.get("home_score") or not g.get("away_score"): continue
        home,away=team(g.get("home_team")),team(g.get("away_team"))
        if not home or not away: continue
        games[week][home]=away
        games[week][away]=home
    # Aggregate all player production by the defense actually faced.
    totals=defaultdict(float)
    for r in stats:
        if str(r.get("season"))!=str(SEASON) or r.get("season_type","REG")!="REG": continue
        try: week=int(r["week"])
        except (KeyError,ValueError): continue
        pos=str(r.get("position") or "").upper()
        if pos not in MARKETS: continue
        offense=team(r.get("team") or r.get("recent_team"))
        defense=team(r.get("opponent_team"))
        if not defense or games.get(week,{}).get(offense)!=defense: continue
        totals[(week,defense,pos)]+=number(r.get(MARKETS[pos]))
    output={}
    for target_week in range(2,19):
        prior=[w for w in sorted(games) if w<target_week]
        if not prior: continue
        for pos,market in MARKETS.items():
            teams=sorted({d for w in prior for d in games[w]})
            records=[]
            for defense in teams:
                history=[(w,totals.get((w,defense,pos),0.0)) for w in prior if defense in games[w]]
                if len(history)<3: continue
                values=[v for _,v in history]
                records.append((defense,len(values),sum(values)/len(values),sum(values[-5:])/len(values[-5:]),len(values[-5:])))
            if not records: continue
            # rank=1 means FEWEST allowed, matching FOURTHDOWN's existing copy.
            records.sort(key=lambda x:(x[2],x[0]))
            for defense,n,avg,last,last_n in records:
                rank=1+sum(other[2]<avg-1e-8 for other in records)
                ties=sum(abs(other[2]-avg)<1e-8 for other in records)
                output[f"{SEASON}|{target_week}|{defense}|{pos}|{market}"]={
                    "rank":rank,"ranked_teams":len(records),"tie_count":ties,
                    "season_allowed_per_game":round(avg,3),"last_5_allowed_per_game":round(last,3),
                    "games":n,"last_5_games":last_n
                }
    if not output: raise RuntimeError("No verified defensive matchup rows; refusing to overwrite published data")
    dest=Path("data/nflverse-defensive-matchups.json");dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps({"season":SEASON,"generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "source":"nflverse","source_url":STATS,"schedule_url":SCHEDULE,
        "rank_definition":"1=fewest yards allowed per game",
        "contexts":output},separators=(",",":"),sort_keys=True)+"\n")
    print(f"Wrote {len(output)} verified pregame contexts")
if __name__=="__main__":main()
