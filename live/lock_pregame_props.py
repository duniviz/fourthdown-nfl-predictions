"""Lock the latest published player projection + verified DK quote before kickoff.

Runs after player research and DraftKings refresh. The history contains the
actual joined numbers used by the Game Center upcoming player cards.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path("data")
KEYS={"Passing yards":"player_pass_yds","Rushing yards":"player_rush_yds","Receiving yards":"player_rec_yds"}
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
    mk=KEYS.get(player.get("market"))
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
    # Never alter any completed-game snapshot. Only replace future game rows
    # when a new fully joined pregame card can be published.
    replacements={}
    for p in research.get("players",[]):
        found=match_quote(p,odds.get("rows",[]),now)
        if not found: continue
        updated,q,kickoff,line=found
        key=(str(p.get("game_id")),str(p.get("player_id")),str(p.get("stat_key")))
        row=dict(p)
        row.update(dk_line=line,dk_quote_time=updated.isoformat(),
                   forecast_captured_at_utc=now.isoformat(),
                   kickoff_utc=kickoff.isoformat(),
                   snapshot_source="matched_published_pregame_card")
        replacements[key]=row
    # Do not replace a previously saved complete snapshot with a forecast
    # that has no verified DK quote in this refresh.
    remaining=[]
    for row in old:
        key=(str(row.get("game_id")),str(row.get("player_id")),str(row.get("stat_key")))
        kickoff=utc(replacements[key].get("kickoff_utc")) if key in replacements else None
        if kickoff and now<kickoff:
            continue
        remaining.append(row)
    remaining.extend(replacements.values())
    path.write_text(json.dumps({"players":remaining},indent=2)+"\n")
    print(f"Saved {len(replacements)} matched pregame projection+DK snapshots")

if __name__=="__main__":
    main()
