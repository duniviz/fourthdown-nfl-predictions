#!/usr/bin/env python3
"""Append verified pre-kickoff player prop snapshots; never backfill after kickoff."""
import datetime as dt
import json
import pathlib
import re
import math

ROOT=pathlib.Path("data")
def read(name,default):
    try: return json.loads((ROOT/name).read_text())
    except (OSError,ValueError): return default
def time(value):
    try: return dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
    except (ValueError,TypeError): return None
def norm(value): return re.sub(r"[^a-z0-9]","",str(value or "").lower())
NICKNAMES={"cardinals":"ARI","falcons":"ATL","ravens":"BAL","bills":"BUF","panthers":"CAR","bears":"CHI","bengals":"CIN","browns":"CLE","cowboys":"DAL","broncos":"DEN","lions":"DET","packers":"GB","texans":"HOU","colts":"IND","jaguars":"JAX","chiefs":"KC","raiders":"LV","chargers":"LAC","rams":"LA","dolphins":"MIA","vikings":"MIN","patriots":"NE","saints":"NO","giants":"NYG","jets":"NYJ","eagles":"PHI","steelers":"PIT","49ers":"SF","seahawks":"SEA","buccaneers":"TB","titans":"TEN","commanders":"WAS"}
def team_code(value):
    return NICKNAMES.get(str(value or '').lower().split()[-1], '')
def main():
    now=dt.datetime.now(dt.timezone.utc)
    odds=read("dk-odds.json",{})
    sources=[("count-projections.json",read("count-projections.json",{})),
             ("yardage-projections.json",read("yardage-projections.json",{}))]
    history=read("player-history.json",{"schema_version":1,"players":[]})
    if not isinstance(history.get("players"),list): history={"schema_version":1,"players":[]}
    if odds.get("bookmaker","").lower()!="draftkings": raise SystemExit("Not DraftKings odds")
    # Only independently timestamped pregame forecasts are eligible; postgame
    # player-results.json must never be used as a forecast source.
    if not isinstance(odds.get("rows"),list): raise SystemExit("Invalid DK odds rows")
    # Count prop market aliases used by the current projection generator.
    aliases={"player_pass_completions":"player_passing_completions","player_pass_attempts":"player_passing_attempts",
             "player_rush_attempts":"player_rushing_attempts","player_receptions":"player_receptions",
             "player_passing_yards":"player_passing_yards","player_rushing_yards":"player_rushing_yards",
             "player_receiving_yards":"player_receiving_yards"}
    odds_aliases={"player_pass_yds":"player_passing_yards",
                  "player_rush_yds":"player_rushing_yards",
                  "player_rec_yds":"player_receiving_yards",
                  "player_pass_completions":"player_passing_completions",
                  "player_pass_attempts":"player_passing_attempts",
                  "player_rush_attempts":"player_rushing_attempts"}
    stat_keys={"player_passing_completions":"completions","player_passing_attempts":"attempts",
               "player_rushing_attempts":"carries","player_receptions":"receptions",
               "player_passing_yards":"passing_yards","player_rushing_yards":"rushing_yards",
               "player_receiving_yards":"receiving_yards"}
    existing={(str(x.get("game_id")),norm(x.get("player")),x.get("stat_key"),str(x.get("dk_line")),str(x.get("dk_quote_time"))) for x in history["players"]}
    added=0
    # Capture throughout the final 35 minutes before kickoff, including late
    # scheduled runs; never capture after kickoff.
    # Existing records remain append-only and are never replaced after kickoff.
    for source_name, projections in sources:
      created=time(projections.get("generated_at_utc"))
      if not created or created>now or not isinstance(projections.get("players"),list):
        continue
      for p in projections.get("players",[]):
        market=aliases.get(p.get("market_key"))
        if not market: continue
        if source_name=="yardage-projections.json" and market not in ("player_passing_yards","player_rushing_yards","player_receiving_yards"): continue
        projection=p.get("projection")
        game_id=str(p.get("game_id") or "")
        if not game_id or not isinstance(projection,(float,int)) or isinstance(projection,bool) or not math.isfinite(projection): continue
        # Game IDs contain away and home team abbreviations; match both teams,
        # not merely a player name that could be reused in another game.
        parts=game_id.split("_")
        if len(parts)<4: continue
        for q in odds["rows"]:
            if norm(q.get("player"))!=norm(p.get("player")) or odds_aliases.get(q.get("market_key"),q.get("market_key"))!=market: continue
            kickoff=time(q.get("commence_time")); quoted=time(q.get("last_update"))
            line=q.get("line")
            if not kickoff or not quoted or not isinstance(line,(int,float)) or isinstance(line,bool) or not math.isfinite(line): continue
            if not (created<kickoff and quoted<kickoff and now<kickoff and quoted<=now): continue
            if not (dt.timedelta(0)<kickoff-now<=dt.timedelta(minutes=35)): continue
            if not (q.get("home_team") and q.get("away_team")): continue
            if q.get('game_id') and str(q['game_id'])!=game_id: continue
            if team_code(q['away_team'])!=parts[2] or team_code(q['home_team'])!=parts[3]: continue
            stat_key=stat_keys[market]
            key=(game_id,norm(p.get("player")),stat_key,str(line),str(q.get("last_update")))
            if key in existing: continue
            history["players"].append({"game_id":game_id,"player":p.get("player"),
                "team":p.get("team"),"player_id":p.get("player_id"),"market_key":market,
                "stat_key":stat_key,"projection":projection,
                "dk_line":line,"recommended_side":"OVER" if projection>line else "UNDER" if projection<line else "NO_PICK",
                "kickoff_utc":q["commence_time"],"forecast_captured_at_utc":projections["generated_at_utc"],
                "dk_quote_time":q["last_update"],"saved_at_utc":now.isoformat(),"bookmaker":"draftkings",
                "source":odds.get("source","ParlayAPI"),"projection_source":source_name})
            existing.add(key);added+=1
    history["players"].sort(key=lambda x:(str(x.get("kickoff_utc")),str(x.get("player")),str(x.get("stat_key")),str(x.get("dk_quote_time"))))
    ROOT.joinpath("player-history.json").write_text(json.dumps(history,indent=2)+"\n")
    print("New verified pregame snapshots:",added,"total:",len(history["players"]))
if __name__=="__main__":main()
