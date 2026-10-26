"""Publish transparent, pregame player yardage baselines (not betting picks).
Only completed prior weeks are used. No sportsbook odds or injury adjustments.
"""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import nflreadpy as nfl

METRICS = (
    ("passing_yards", "Passing yards", "attempts"),
    ("rushing_yards", "Rushing yards", "carries"),
    ("receiving_yards", "Receiving yards", "targets"),
)
def num(x):
    try: return float(x or 0)
    except (TypeError, ValueError): return 0.0

def generate():
    now=datetime.now(timezone.utc)
    season=now.year if now.month>=3 else now.year-1
    schedule=nfl.load_schedules([season]).to_dicts()
    from zoneinfo import ZoneInfo
    games=[]
    for g in schedule:
        if g.get("game_type")!="REG": continue
        try:
            dt=datetime.fromisoformat(str(g["gameday"])+"T"+str(g["gametime"])).replace(tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)
        except (ValueError, KeyError, TypeError): continue
        if dt>now: games.append((dt,g))
    games.sort(key=lambda x:x[0])
    if not games: raise ValueError("No upcoming games")
    week=int(games[0][1]["week"])
    games=[g for dt,g in games if int(g["week"])==week]
    rows=nfl.load_player_stats([season],summary_level="week").to_dicts()
    history=defaultdict(list)
    opponents=defaultdict(lambda:defaultdict(list))
    for r in rows:
        try: w=int(r["week"])
        except (KeyError,ValueError,TypeError): continue
        if w>=week or str(r.get("season_type","REG")).upper() not in ("REG","2"): continue
        team=str(r.get("team") or "")
        opp=str(r.get("opponent_team") or "")
        player=str(r.get("player_id") or "")
        if not team or not player: continue
        history[(team,player)].append(r)
        for metric,_,_ in METRICS:
            if opp: opponents[opp][metric].append(num(r.get(metric)))
    # nflverse player registry maps GSIS player IDs in weekly stats to ESPN
    # athlete IDs used by ESPN's public headshot CDN. Fail open to initials.
    espn_ids={}
    try:
        registry=nfl.load_players().to_dicts()
        for athlete in registry:
            gsis=str(athlete.get("gsis_id") or athlete.get("player_id") or "").strip()
            espn=str(athlete.get("espn_id") or "").strip()
            if gsis and espn.isdigit():
                espn_ids[gsis]=espn
        print(f"Mapped {len(espn_ids)} player IDs to ESPN headshots")
    except Exception as exc:
        print(f"Player headshot lookup unavailable: {exc}")
    results=[]
    for game in games:
        for team,opp in ((game["home_team"],game["away_team"]),(game["away_team"],game["home_team"])):
            for (t,player),stats in history.items():
                if t!=team: continue
                stats=sorted(stats,key=lambda x:int(x["week"]))
                if len(stats)<3: continue
                for metric,label,volume in METRICS:
                    last=stats[-5:]
                    values=[num(x.get(metric)) for x in last]
                    avg=sum(values)/len(values)
                    if avg< (85 if metric=="passing_yards" else 18): continue
                    v=[num(x.get(volume)) for x in last]
                    # Opponent allowed yards per player appearance is descriptive, not
                    # position-adjusted; do not use it as an unvalidated multiplier.
                    opp_values=opponents[opp][metric]
                    baseline=0.55*(sum(values[-3:])/min(3,len(values)))+0.45*avg
                    results.append({
                        "game_id":str(game["game_id"]),"team":team,"opponent":opp,
                        "player_id":player,
                        "espn_athlete_id":espn_ids.get(player),
                        "player":stats[-1].get("player_display_name") or stats[-1].get("player_name") or player,
                        "position":stats[-1].get("position"),
                        "market":label,"stat_key":metric,"games_used":len(stats),
                        "last_5":[round(x,1) for x in values],
                        "last_5_avg":round(avg,1),
                        "last_3_avg":round(sum(values[-3:])/min(3,len(values)),1),
                        "last_5_opportunities_avg":round(sum(v)/len(v),1),
                        "opportunity_type":volume,
                        "opponent_player_appearance_avg":round(sum(opp_values)/len(opp_values),1) if len(opp_values)>=10 else None,
                        "projection":round(baseline,1),
                        "method":"55% last-three average + 45% last-five average; uncalibrated research baseline",
                        "bet_recommendation":False,
                    })
    results.sort(key=lambda x:(x["game_id"],x["team"],x["market"],-x["projection"]))
    out={"generated_at_utc":now.isoformat(),"season":season,"week":week,"status":"research_only_no_market_odds","players":results}
    p=Path("data/player-research.json");p.parent.mkdir(exist_ok=True)
    archive_path=Path("data/player-history.json")
    try:
        existing=json.loads(archive_path.read_text(encoding="utf-8"))
        old=existing.get("players",[])
    except (OSError,ValueError,TypeError):
        old=[]
    # Preserve original pregame forecasts; never rewrite past predictions.
    seen={(str(x.get("game_id")),str(x.get("player_id")),str(x.get("stat_key"))) for x in old}
    for item in results:
        key=(str(item["game_id"]),str(item["player_id"]),str(item["stat_key"]))
        if key not in seen:
            old.append(item)
            seen.add(key)
    archive_path.write_text(json.dumps({"players":old},indent=2)+"\n",encoding="utf-8")
    p.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(f"Published {len(results)} player baselines for week {week}")

if __name__=="__main__": generate()
