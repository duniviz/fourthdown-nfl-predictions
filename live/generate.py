"""Produce upcoming-game FOURTHDOWN v2 projections from current-season nflverse data."""
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from live.injury_adjust import estimate

def number(x):
    try:
        y=float(x)
        return y if math.isfinite(y) else None
    except (ValueError, TypeError):
        return None


def build_team_matchup_metrics(schedules, plays, season, target_week):
    """Build descriptive pregame team ranks; these values do not affect v2 scoring."""
    stats=defaultdict(lambda:defaultdict(float))
    completed=[]
    for game in schedules:
        try:
            week=int(game.get("week",0))
        except (TypeError,ValueError):
            continue
        home,away=game.get("home_team"),game.get("away_team")
        hs,ass=number(game.get("home_score")),number(game.get("away_score"))
        if int(game.get("season",0))==season and week<target_week and home and away and hs is not None and ass is not None:
            completed.append(game)
            for team,pf,pa in ((home,hs,ass),(away,ass,hs)):
                stats[team]["games"]+=1
                stats[team]["points_for"]+=pf
                stats[team]["points_against"]+=pa
    red_zone_drives={}
    for row in plays or []:
        try:
            if int(row.get("season",0))!=season or int(row.get("week",0))>=target_week: continue
        except (TypeError,ValueError):
            continue
        off,defn=row.get("posteam"),row.get("defteam")
        if not off or not defn or row.get("play_type") not in ("pass","run"): continue
        yards=number(row.get("yards_gained")) or 0.0
        epa=number(row.get("epa"))
        stats[off]["plays"]+=1; stats[off]["yards"]+=yards
        stats[defn]["plays_allowed"]+=1; stats[defn]["yards_allowed"]+=yards
        if epa is not None:
            stats[off]["epa"]+=epa; stats[off]["epa_plays"]+=1
            stats[defn]["epa_allowed"]+=epa; stats[defn]["epa_allowed_plays"]+=1
        phase="pass" if row.get("play_type")=="pass" else "rush"
        if epa is not None:
            stats[off][phase+"_epa"]+=epa; stats[off][phase+"_plays"]+=1
            stats[defn][phase+"_epa_allowed"]+=epa; stats[defn][phase+"_allowed_plays"]+=1
        if number(row.get("sack"))==1:
            stats[off]["sacks_allowed"]+=1; stats[defn]["sacks"]+=1
        if number(row.get("interception"))==1 or number(row.get("fumble_lost"))==1:
            stats[off]["giveaways"]+=1; stats[defn]["takeaways"]+=1
        down=number(row.get("down"))
        converted=number(row.get("first_down"))==1 or number(row.get("touchdown"))==1
        if down in (3,4):
            key="third" if down==3 else "fourth"
            stats[off][key+"_attempts"]+=1; stats[defn][key+"_allowed_attempts"]+=1
            if converted:
                stats[off][key+"_conversions"]+=1; stats[defn][key+"_allowed_conversions"]+=1
        yardline=number(row.get("yardline_100"))
        drive=row.get("drive")
        if yardline is not None and yardline<=20 and drive is not None:
            key=(str(row.get("game_id","")),off,str(drive))
            red_zone_drives.setdefault(key,{"team":off,"defense":defn,"td":False})
            if number(row.get("touchdown"))==1: red_zone_drives[key]["td"]=True
    for drive in red_zone_drives.values():
        stats[drive["team"]]["red_zone_drives"]+=1
        stats[drive["defense"]]["red_zone_drives_allowed"]+=1
        if drive["td"]:
            stats[drive["team"]]["red_zone_tds"]+=1
            stats[drive["defense"]]["red_zone_tds_allowed"]+=1
    def ratio(num,den):
        return None if not den else num/den
    values={}
    for team,row in stats.items():
        games=row["games"]
        if not games: continue
        values[team]={
            "points":(ratio(row["points_for"],games),ratio(row["points_against"],games),"pts/g"),
            "yards_per_play":(ratio(row["yards"],row["plays"]),ratio(row["yards_allowed"],row["plays_allowed"]),"yds/play"),
            "epa_per_play":(ratio(row["epa"],row["epa_plays"]),ratio(row["epa_allowed"],row["epa_allowed_plays"]),"EPA/play"),
            "pass_epa":(ratio(row["pass_epa"],row["pass_plays"]),ratio(row["pass_epa_allowed"],row["pass_allowed_plays"]),"EPA/pass"),
            "rush_epa":(ratio(row["rush_epa"],row["rush_plays"]),ratio(row["rush_epa_allowed"],row["rush_allowed_plays"]),"EPA/rush"),
            "sacks":(ratio(row["sacks_allowed"],games),ratio(row["sacks"],games),"sacks/g"),
            "turnovers":(ratio(row["giveaways"],games),ratio(row["takeaways"],games),"TO/g"),
            "third_down":(ratio(row["third_conversions"],row["third_attempts"]),ratio(row["third_allowed_conversions"],row["third_allowed_attempts"]),"%"),
            "fourth_down":(ratio(row["fourth_conversions"],row["fourth_attempts"]),ratio(row["fourth_allowed_conversions"],row["fourth_allowed_attempts"]),"%"),
            "red_zone_td":(ratio(row["red_zone_tds"],row["red_zone_drives"]),ratio(row["red_zone_tds_allowed"],row["red_zone_drives_allowed"]),"%"),
        }
    definitions=[
        ("total","Points / game","points",True,False),
        ("total","Yards / play","yards_per_play",True,False),
        ("epa","EPA / play","epa_per_play",True,False),
        ("epa","EPA / pass","pass_epa",True,False),
        ("epa","EPA / rush","rush_epa",True,False),
        ("negative","Sacks / game","sacks",False,True),
        ("negative","Turnovers / game","turnovers",False,True),
        ("conversion","3rd down conversion","third_down",True,False),
        ("conversion","4th down conversion","fourth_down",True,False),
        ("conversion","Red-zone TD rate","red_zone_td",True,False),
    ]
    rankings={}
    for _,_,key,off_high,def_high in definitions:
        offense=sorted(((team,data[key][0]) for team,data in values.items() if data[key][0] is not None),key=lambda item:item[1],reverse=off_high)
        defense=sorted(((team,data[key][1]) for team,data in values.items() if data[key][1] is not None),key=lambda item:item[1],reverse=def_high)
        rankings[key]={"offense":{team:i+1 for i,(team,_) in enumerate(offense)},"defense":{team:i+1 for i,(team,_) in enumerate(defense)}}
    return values,rankings,definitions

def forecast(schedules, team_games, now=None, injury_reports=None, player_weekly=None, team_metric_rows=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None: raise ValueError("now must be timezone-aware")
    season=now.year if now.month>=3 else now.year-1
    games=[g for g in schedules if int(g["season"])==season and g.get("game_type")=="REG"]
    if not games: raise ValueError("No current-season regular season schedule")
    upcoming=[]
    for g in games:
        dt=g.get("gameday")
        tm=g.get("gametime")
        if not dt or not tm: continue
        # nflverse schedule dates/times are Eastern; prefer game datetime when available.
        from datetime import date, time
        from zoneinfo import ZoneInfo
        try:
            local=datetime.fromisoformat(str(dt)+"T"+str(tm)).replace(tzinfo=ZoneInfo("America/New_York"))
        except ValueError:
            continue
        if local.astimezone(timezone.utc)>now:
            upcoming.append((local,g))
    upcoming.sort(key=lambda item:item[0])
    if not upcoming: raise ValueError("No upcoming scheduled games: do not overwrite previous data")
    # Only include prior completed weeks. Prevent partial-week results from
    # affecting other matchups in the same week (as in historical v2).
    target_week=int(upcoming[0][1]["week"])
    target_games=[(dt,g) for dt,g in upcoming if int(g["week"])==target_week]
    prior=defaultdict(list)
    for r in team_games:
        if int(r["season"])!=season or int(r["week"])>=target_week: continue
        off,defn=number(r.get("offense_epa")),number(r.get("defense_epa"))
        if off is not None and defn is not None:
            prior[int(r["week"])].append((r["team"],off,defn))
    # Verify prior EPA rows are paired with completed schedule results.
    complete={(int(g["week"]),g["home_team"],g["away_team"]) for g in games
              if int(g["week"])<target_week and number(g.get("home_score")) is not None
              and number(g.get("away_score")) is not None}
    histories=defaultdict(list)
    for week in sorted(prior):
        valid_teams={t for w,h,a in complete if w==week for t in (h,a)}
        records=[r for r in prior[week] if r[0] in valid_teams]
        if not records: continue
        def rating(team):
            hist=histories[team]
            weights=[2**(-(week-w-1)/4.0) for w,_,_ in hist]
            den=4.0+sum(weights)
            return (sum(weight*off for weight,(_,off,_) in zip(weights,hist))/den,
                    sum(weight*de for weight,(_,_,de) in zip(weights,hist))/den)
        current={t:rating(t) for t,_,_ in records}
        # opponent pairing only for the relevant week's completed matchups
        records_by_team={t:(off,de) for t,off,de in records}
        for w,home,away in complete:
            if w!=week or home not in records_by_team or away not in records_by_team: continue
            ho,hd=current[home];ao,ad=current[away]
            he,hed=records_by_team[home];ae,aed=records_by_team[away]
            histories[home].append((week,he-.5*ad,hed-.5*ao))
            histories[away].append((week,ae-.5*hd,aed-.5*ho))
    def rating(team):
        hist=histories[team]
        weights=[2**(-(target_week-w-1)/4.0) for w,_,_ in hist]
        den=4.0+sum(weights)
        return (sum(weight*off for weight,(_,off,_) in zip(weights,hist))/den,
                sum(weight*de for weight,(_,_,de) in zip(weights,hist))/den,len(hist))
    # Transparent, pregame-only team form; completed prior weeks only.
    form=defaultdict(list)
    for g in games:
        w=int(g["week"])
        if w>=target_week or (w,g["home_team"],g["away_team"]) not in complete: continue
        hs,ass=number(g.get("home_score")),number(g.get("away_score"))
        if hs is None or ass is None: continue
        form[g["home_team"]].append((w,hs,ass))
        form[g["away_team"]].append((w,ass,hs))
    def team_form(team):
        recent=sorted(form[team],key=lambda x:x[0])[-5:]
        if not recent: return None
        return {"games":len(recent),"wins":sum(pf>pa for _,pf,pa in recent),
                "avg_points_for":round(sum(pf for _,pf,pa in recent)/len(recent),1),
                "avg_points_against":round(sum(pa for _,pf,pa in recent)/len(recent),1),
                "avg_margin":round(sum(pf-pa for _,pf,pa in recent)/len(recent),1),
                "results":[{"week":w,"points_for":int(pf),"points_against":int(pa),"result":"W" if pf>pa else "L" if pf<pa else "T"} for w,pf,pa in recent]}
    # Rank all clubs with enough prior observations; lower defensive EPA is better.
    eligible={t:rating(t) for t in set(form)|set(histories)}
    eligible={t:v for t,v in eligible.items() if v[2]>=3}
    offensive_order=sorted(eligible,key=lambda t:eligible[t][0],reverse=True)
    defensive_order=sorted(eligible,key=lambda t:eligible[t][1])
    offense_rank={t:i+1 for i,t in enumerate(offensive_order)}
    defense_rank={t:i+1 for i,t in enumerate(defensive_order)}
    metric_values,metric_rankings,metric_definitions=build_team_matchup_metrics(games,team_metric_rows,season,target_week)
    def matchup_metrics(away,home):
        rows=[]
        for category,label,key,_,_ in metric_definitions:
            av=metric_values.get(away,{}).get(key); hv=metric_values.get(home,{}).get(key)
            if not av or not hv: continue
            ar=metric_rankings.get(key,{}).get("offense",{}).get(away)
            hd=metric_rankings.get(key,{}).get("defense",{}).get(home)
            hr=metric_rankings.get(key,{}).get("offense",{}).get(home)
            ad=metric_rankings.get(key,{}).get("defense",{}).get(away)
            if None in (ar,hd,hr,ad): continue
            unit=av[2]
            rows.append({"category":category,"label":label,"unit":unit,
                "away_offense":{"rank":ar,"value":round(av[0]*100,1) if unit=="%" else round(av[0],2)},
                "home_defense":{"rank":hd,"value":round(hv[1]*100,1) if unit=="%" else round(hv[1],2)},
                "home_offense":{"rank":hr,"value":round(hv[0]*100,1) if unit=="%" else round(hv[0],2)},
                "away_defense":{"rank":ad,"value":round(av[1]*100,1) if unit=="%" else round(av[1],2)}})
        return rows
    results=[]
    injury_reports=injury_reports or {}
    player_weekly=player_weekly or []
    for dt,g in target_games:
        ho,hd,hn=rating(g["home_team"])
        ao,ad,an=rating(g["away_team"])
        if min(hn,an)<3: continue
        home_epa=ho+ad;away_epa=ao+hd
        margin=1.5+45*(home_epa-away_epa)
        total=max(1.0,44+45*(home_epa+away_epa))
        home_points=max(0,(total+margin)/2)
        away_points=max(0,(total-margin)/2)
        adjustments={}
        for team in (g["home_team"],g["away_team"]):
            report=injury_reports.get(team,{})
            if report.get("status")!="retrieved":
                adjustments[team]={"points":0.0,"status":"injury_feed_unavailable","players":[]}
            else:
                adjustments[team]=estimate(team,report.get("players",[]),player_weekly,games,target_week)
        home_points=max(0,home_points+adjustments[g["home_team"]]["points"])
        away_points=max(0,away_points+adjustments[g["away_team"]]["points"])
        margin=home_points-away_points
        total=home_points+away_points
        results.append({"game_id":str(g["game_id"]),"season":season,"week":target_week,
            "kickoff_utc":dt.astimezone(timezone.utc).isoformat(),
            "home":g["home_team"],"away":g["away_team"],
            "projected_home_score":round(home_points,1),
            "projected_away_score":round(away_points,1),
            "projected_margin_home":round(margin,2),"projected_total":round(total,2),
            "predicted_winner":g["home_team"] if margin>0 else g["away_team"],
            "injury_adjustments":adjustments,
            "analysis":{"home":{"team":g["home_team"],"games_used":hn,"offense_epa_rating":round(ho,4),"defense_epa_rating":round(hd,4),"offense_rank":offense_rank.get(g["home_team"]),"defense_rank":defense_rank.get(g["home_team"]),"ranked_teams":len(eligible),"recent_form":team_form(g["home_team"])},
                        "away":{"team":g["away_team"],"games_used":an,"offense_epa_rating":round(ao,4),"defense_epa_rating":round(ad,4),"offense_rank":offense_rank.get(g["away_team"]),"defense_rank":defense_rank.get(g["away_team"]),"ranked_teams":len(eligible),"recent_form":team_form(g["away_team"])},
                        "matchup_metrics":matchup_metrics(g["away_team"],g["home_team"]),
                        "estimated_home_advantage_points":1.5,
                        "scoring_edge_components":{"home_offense_vs_away_defense":round(45*(ho+ad),2),"away_offense_vs_home_defense":round(45*(ao+hd),2),"home_field_points":1.5},
                        "method":"Recency-weighted, opponent-adjusted EPA per play with shrinkage; recent form uses last five completed prior games."}})
    if not results: raise ValueError("Insufficient completed games for v2; do not publish")
    return {"model":"FOURTHDOWN v2","generated_at_utc":now.isoformat(),
            "season":season,"week":target_week,"status":"research_uncalibrated",
            "note":"Pregame EPA projections with experimental QB injury splits when data supports them; other injuries and weather not numerically adjusted.",
            "games":results}

def main():
    import nflreadpy as nfl
    import polars as pl
    now=datetime.now(timezone.utc)
    season=now.year if now.month>=3 else now.year-1
    schedules=nfl.load_schedules([season]).to_dicts()
    pbp=nfl.load_pbp([season])
    needed={"season","week","game_id","posteam","defteam","epa","play_type"}
    if needed-set(pbp.columns): raise ValueError("Missing required PBP columns")
    metric_columns=[c for c in ("season","week","game_id","posteam","defteam","play_type","yards_gained","epa","sack","interception","fumble_lost","down","first_down","touchdown","yardline_100","drive") if c in pbp.columns]
    team_metric_rows=pbp.select(metric_columns).to_dicts()
    base=pbp.filter(pl.col("play_type").is_in(["pass","run"]) &
                    pl.col("epa").is_not_null() &
                    pl.col("posteam").is_not_null() &
                    pl.col("defteam").is_not_null())
    offense=base.group_by(["season","week","game_id","posteam"]).agg(pl.col("epa").mean().alias("offense_epa")).rename({"posteam":"team"})
    defense=base.group_by(["season","week","game_id","defteam"]).agg(pl.col("epa").mean().alias("defense_epa")).rename({"defteam":"team"})
    epa=offense.join(defense,on=["season","week","game_id","team"],how="inner").to_dicts()
    injury_reports={}
    injury_path=Path("data/injuries.json")
    if injury_path.exists():
        try:
            feed=json.loads(injury_path.read_text(encoding="utf-8"))
            age=(now-datetime.fromisoformat(feed["generated_at_utc"].replace("Z","+00:00"))).total_seconds()/3600
            if 0<=age<=24:
                injury_reports=feed.get("teams",{})
        except (ValueError,KeyError,TypeError):
            pass
    weekly=nfl.load_player_stats([season],summary_level="week").to_dicts() if injury_reports else []
    data=forecast(schedules,epa,now,injury_reports,weekly,team_metric_rows)
    dest=Path("data/live-v2.json")
    dest.parent.mkdir(parents=True,exist_ok=True)
    # Keep immutable first-published predictions for transparent future grading.
    archive_path=Path("data/v2-history.json")
    archive={"model":"FOURTHDOWN v2","games":[]}
    if archive_path.exists():
        archive=json.loads(archive_path.read_text(encoding="utf-8"))
    existing={str(g.get("game_id")) for g in archive.get("games",[])}
    for game in data["games"]:
        if game["game_id"] not in existing:
            archive["games"].append({**game,"published_at_utc":data["generated_at_utc"]})
            existing.add(game["game_id"])
    archive_path.write_text(json.dumps(archive,indent=2)+"\n",encoding="utf-8")
    dest.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print(f"Generated {len(data['games'])} v2 forecasts for {season} week {data['week']}")

if __name__=="__main__":main()
