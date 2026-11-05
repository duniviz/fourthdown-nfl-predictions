"""Lock the latest published player projection + verified DK quote before kickoff.

Runs after player research and DraftKings refresh. The history contains the
actual joined numbers used by the Game Center upcoming player cards.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path("data")
KEYS={"Passing yards":"player_pass_yds","Rushing yards":"player_rush_yds","Receiving yards":"player_rec_yds",
      "Completions":"player_passing_completions","Rush attempts":"player_rushing_attempts","Receptions":"player_receptions"}
TEAMS={"ARI":"Arizona Cardinals","ATL":"Atlanta Falcons","BAL":"Baltimore Ravens","BUF":"Buffalo Bills","CAR":"Carolina Panthers","CHI":"Chicago Bears","CIN":"Cincinnati Bengals","CLE":"Cleveland Browns","DAL":"Dallas Cowboys","DEN":"Denver Broncos","DET":"Detroit Lions","GB":"Green Bay Packers","HOU":"Houston Texans","IND":"Indianapolis Colts","JAC":"Jacksonville Jaguars","JAX":"Jacksonville Jaguars","KC":"Kansas City Chiefs","LV":"Las Vegas Raiders","LAC":"Los Angeles Chargers","LAR":"Los Angeles Rams","LA":"Los Angeles Rams","MIA":"Miami Dolphins","MIN":"Minnesota Vikings","NE":"New England Patriots","NO":"New Orleans Saints","NYG":"New York Giants","NYJ":"New York Jets","PHI":"Philadelphia Eagles","PIT":"Pittsburgh Steelers","SF":"San Francisco 49ers","SEA":"Seattle Seahawks","TB":"Tampa Bay Buccaneers","TEN":"Tennessee Titans","WAS":"Washington Commanders"}

def norm(v):
    return "".join(c for c in str(v or "").lower() if c.isalnum())

def utc(v):
    try:
        d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (TypeError,ValueError):
        return None

def team(v):
    return norm(TEAMS.get(str(v).upper(),v))

def match_quote(player,quotes,now):
    mk=player.get("market_key") if player.get("market_key") in ("player_pass_completions","player_rush_attempts","player_receptions") else KEYS.get(player.get("market"))
    if mk=="player_pass_completions": mk="player_passing_completions"
    if mk=="player_rush_attempts": mk="player_rushing_attempts"
    if not mk:
        return None
    matches=[]
    for q in quotes:
        kickoff=utc(q.get("commence_time"))
        updated=utc(q.get("last_update"))
        try: line=float(q.get("line"))
        except (TypeError,ValueError): continue
        if not kickoff or not updated or not (updated<=now<kickoff) or not (line>0):
            continue
        if q.get("market_key")!=mk or norm(q.get("player"))!=norm(player.get("player")):
            continue
        pair={team(q.get("home_team")),team(q.get("away_team"))}
        if "" in pair or pair!={team(player.get("team")),team(player.get("opponent"))}:
            continue
        matches.append((updated,q,kickoff,line))
    if not matches:
        return None
    matches.sort(key=lambda m:m[0],reverse=True)
    return matches[0]

def main():
    now=datetime.now(timezone.utc)
    research=json.loads((ROOT/"player-research.json").read_text())
    odds=json.loads((ROOT/"dk-odds.json").read_text())
    path=ROOT/"player-history.json"
    history=json.loads(path.read_text()) if path.exists() else {"players":[]}
    old=history.get("players",[])
    if not isinstance(old,list): old=[]
    # Merge the separately published count projections into the same pregame
    # archive. Do not synthesize lines or retroactively archive finished games.
    count_path=ROOT/"count-projections.json"
    count=json.loads(count_path.read_text()) if count_path.exists() else {"players":[]}
    count_markets={"player_pass_completions":("completions","Completions"),
                   "player_rush_attempts":("carries","Rush attempts"),
                   "player_receptions":("receptions","Receptions")}
    candidates=list(research.get("players",[]))
    for item in count.get("players",[]):
        market=count_markets.get(item.get("market_key"))
        if not market: continue
        row=dict(item)
        row.update(stat_key=market[0],market=market[1],
                   last_5_avg=item.get("recent_5_avg"),
                   snapshot_source="count_projections")
        candidates.append(row)
    # Preserve every valid pre-kickoff observation, including earlier quotes.
    # Re-running a workflow with the same forecast and quote is idempotent.
    existing = {
        (str(x.get("game_id")), str(x.get("player_id")), str(x.get("stat_key")),
         str(x.get("forecast_captured_at_utc")), str(x.get("dk_quote_time")))
        for x in old
    }
    added = 0
    for p in candidates:
        found = match_quote(p, odds.get("rows", []), now)
        if not found:
            continue
        updated, q, kickoff, line = found
        forecast_time = utc(count.get("generated_at_utc") if p.get("snapshot_source") == "count_projections" else research.get("generated_at_utc"))
        if not forecast_time or not (forecast_time <= now and forecast_time < kickoff and updated < kickoff):
            continue
        key = (str(p.get("game_id")), str(p.get("player_id")), str(p.get("stat_key")),
               forecast_time.isoformat(), updated.isoformat())
        if key in existing:
            continue
        row = dict(p)
        row.update(recommended_side="OVER" if float(p["projection"])>line else "UNDER" if float(p["projection"])<line else "NO_PICK",
                   dk_line=line, dk_quote_time=updated.isoformat(),
                   forecast_captured_at_utc=forecast_time.isoformat(),
                   kickoff_utc=kickoff.isoformat(),
                   snapshot_source="matched_published_pregame_card")
        old.append(row)
        existing.add(key)
        added += 1
    path.write_text(json.dumps({"players": old}, indent=2) + "\n")
    print(f"Appended {added} pregame observations; retained {len(old)} total")

if __name__=="__main__":
    main()
