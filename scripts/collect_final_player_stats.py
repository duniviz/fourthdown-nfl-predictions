#!/usr/bin/env python3
"""Collect completed NFL box-score player stats without changing frozen predictions."""
import json, pathlib, re, urllib.request
from datetime import datetime, timezone
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
def load(name):
    try: return json.loads((DATA/name).read_text())
    except (OSError,ValueError): return {}
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"FOURTHDOWN-results/1.0"})
    with urllib.request.urlopen(req,timeout=25) as r: return json.load(r)
def canon(s): return re.sub(r"[^A-Z0-9]","",str(s or "").upper())
def main():
    games=load("v2-history.json").get("games",[])
    archived=load("player-history.json").get("players",[])
    results=load("player-results.json").get("rows",[])
    targets={str(g.get("game_id")):g for g in games}
    for row in archived:
        key=str(row.get("game_id",""))
        if key not in targets and re.match(r"^\d{4}_\d{2}_[A-Z]+_[A-Z]+$",key):
            year,week,away,home=key.split("_")
            targets[key]={"game_id":key,"season":int(year),"week":int(week),"away":away,"home":home}
    by_game={}
    for g in targets.values():
        if not g.get("season") or not g.get("week"):continue
        by_game.setdefault((int(g["season"]),int(g["week"])),[]).append(g)
    output=load("player-final-stats.json")
    saved={(str(x.get("game_id")),canon(x.get("player")),str(x.get("stat_key"))):x for x in output.get("rows",[])}
    for (year,week),group in by_game.items():
        try: board=fetch(f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={year}&seasontype=2&week={week}&limit=100")
        except Exception as e:
            print(f"Scoreboard unavailable {year} week {week}: {e}");continue
        for event in board.get("events",[]):
            if not event.get("status",{}).get("type",{}).get("completed"):continue
            comp=(event.get("competitions") or [{}])[0]
            teams={x.get("homeAway"):canon(x.get("team",{}).get("abbreviation")) for x in comp.get("competitors",[])}
            matches=[g for g in group if canon(g.get("home"))==teams.get("home") and canon(g.get("away"))==teams.get("away")]
            if not matches:continue
            try: detail=fetch(f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={event['id']}")
            except Exception as e:
                print(f"Box score unavailable {event['id']}: {e}");continue
            # Participation evidence is separate from yardage rows. Never infer a
            # zero merely because ESPN omitted a player from a stat category.
            participants=set()
            for side in detail.get("boxscore",{}).get("players",[]):
                for category in side.get("statistics",[]):
                    for athlete in category.get("athletes",[]):
                        if athlete.get("stats"):
                            participants.add(canon(athlete.get("athlete",{}).get("displayName")))
            for g in matches:
                for pick in archived:
                    if str(pick.get("game_id"))!=str(g["game_id"]):continue
                    name=pick.get("player")
                    stat=pick.get("stat_key")
                    if not name or stat not in ("passing_yards","rushing_yards","receiving_yards"):continue
                    if canon(name) not in participants:continue
                    key=(str(g["game_id"]),canon(name),stat)
                    # A player who appears in another statistical category is
                    # confirmed to have participated, but a missing market still
                    # requires a separately verified zero, not an assumption.
                    if key not in saved:
                        print(f"Participation confirmed; {name} {stat} missing, zero unverified")
            for side in detail.get("boxscore",{}).get("players",[]):
                for cat in side.get("statistics",[]):
                    label=canon(cat.get("name"))
                    if label not in ("PASSING","RUSHING","RECEIVING"):continue
                    headers=[canon(x) for x in cat.get("labels",[])]
                    for athlete in cat.get("athletes",[]):
                        player=athlete.get("athlete",{}).get("displayName")
                        stats=athlete.get("stats",[])
                        if not player or not stats:continue
                        # ESPN's passing/rushing/receiving box scores have YDS columns.
                        try: idx=headers.index("YDS")
                        except ValueError:continue
                        if idx>=len(stats):continue
                        try: yards=float(str(stats[idx]).replace(",",""))
                        except ValueError:continue
                        stat_key=label.lower()+"_yards"
                        for g in matches:
                            key=(str(g["game_id"]),canon(player),stat_key)
                            saved[key]={"game_id":str(g["game_id"]),"player":player,"stat_key":stat_key,"actual":yards,"source":"ESPN final box score","event_id":str(event["id"])}
    output={"updated_at_utc":datetime.now(timezone.utc).isoformat(),"rows":sorted(saved.values(),key=lambda x:(x["game_id"],x["player"],x["stat_key"]))}
    (DATA/"player-final-stats.json").write_text(json.dumps(output,indent=2)+"\n")
    print(f"Saved {len(saved)} verified player stat rows")
if __name__=="__main__":main()
