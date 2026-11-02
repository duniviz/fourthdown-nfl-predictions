#!/usr/bin/env python3
"""Append verified pre-kickoff player prop snapshots; never backfill after kickoff."""
import datetime as dt
import json
import pathlib
import re

ROOT=pathlib.Path("data")
def read(name,default):
    try: return json.loads((ROOT/name).read_text())
    except (OSError,ValueError): return default
def time(value):
    try: return dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
    except (ValueError,TypeError): return None
def norm(value): return re.sub(r"[^a-z0-9]","",str(value or "").lower())
def main():
    now=dt.datetime.now(dt.timezone.utc)
    odds=read("dk-odds.json",{})
    projections=read("count-projections.json",{})
    history=read("player-history.json",{"schema_version":1,"players":[]})
    if not isinstance(history.get("players"),list): history={"schema_version":1,"players":[]}
    if odds.get("bookmaker","").lower()!="draftkings": raise SystemExit("Not DraftKings odds")
    created=time(projections.get("generated_at_utc"))
    if not created or created>now: raise SystemExit("Invalid projection timestamp")
    # Count prop market aliases used by the current projection generator.
    aliases={"player_pass_completions":"player_passing_completions","player_pass_attempts":"player_passing_attempts",
             "player_rush_attempts":"player_rushing_attempts","player_receptions":"player_receptions",
             "player_passing_yards":"player_passing_yards","player_rushing_yards":"player_rushing_yards",
             "player_receiving_yards":"player_receiving_yards"}
    existing={(str(x.get("game_id")),norm(x.get("player")),x.get("stat_key"),str(x.get("dk_line")),str(x.get("dk_quote_time"))) for x in history["players"]}
    added=0
    for p in projections.get("players",[]):
        market=aliases.get(p.get("market_key"))
        if not market: continue
        projection=p.get("projection")
        if not isinstance(projection,(float,int)): continue
        for q in odds.get("rows",[]):
            if norm(q.get("player"))!=norm(p.get("player")) or q.get("market_key")!=market: continue
            kickoff=time(q.get("commence_time")); quoted=time(q.get("last_update"))
            line=q.get("line")
            if not kickoff or not quoted or not isinstance(line,(int,float)): continue
            if not (created<kickoff and quoted<kickoff and now<kickoff and quoted<=now): continue
            key=(str(p.get("game_id")),norm(p.get("player")),market,str(line),str(q.get("last_update")))
            if key in existing: continue
            history["players"].append({"game_id":p.get("game_id"),"player":p.get("player"),
                "team":p.get("team"),"stat_key":market,"projection":projection,
                "dk_line":line,"recommended_side":"OVER" if projection>line else "UNDER" if projection<line else "NO_PICK",
                "kickoff_utc":q["commence_time"],"forecast_captured_at_utc":projections["generated_at_utc"],
                "dk_quote_time":q["last_update"],"saved_at_utc":now.isoformat(),"bookmaker":"draftkings",
                "source":odds.get("source","ParlayAPI")})
            existing.add(key);added+=1
    history["players"].sort(key=lambda x:(str(x.get("kickoff_utc")),str(x.get("player")),str(x.get("stat_key")),str(x.get("dk_quote_time"))))
    ROOT.joinpath("player-history.json").write_text(json.dumps(history,indent=2)+"\n")
    print("New verified pregame snapshots:",added,"total:",len(history["players"]))
if __name__=="__main__":main()
