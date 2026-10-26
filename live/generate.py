"""Produce upcoming-game FOURTHDOWN v2 projections from current-season nflverse data."""
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

def number(x):
    try:
        y=float(x)
        return y if math.isfinite(y) else None
    except (ValueError, TypeError):
        return None

def forecast(schedules, team_games, now=None):
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
    results=[]
    for dt,g in target_games:
        ho,hd,hn=rating(g["home_team"])
        ao,ad,an=rating(g["away_team"])
        if min(hn,an)<3: continue
        home_epa=ho+ad;away_epa=ao+hd
        margin=1.5+45*(home_epa-away_epa)
        total=max(1.0,44+45*(home_epa+away_epa))
        home_points=max(0,(total+margin)/2)
        away_points=max(0,(total-margin)/2)
        results.append({"game_id":str(g["game_id"]),"season":season,"week":target_week,
            "kickoff_utc":dt.astimezone(timezone.utc).isoformat(),
            "home":g["home_team"],"away":g["away_team"],
            "projected_home_score":round(home_points,1),
            "projected_away_score":round(away_points,1),
            "projected_margin_home":round(margin,2),"projected_total":round(total,2),
            "predicted_winner":g["home_team"] if margin>0 else g["away_team"],
            "analysis":{"home":{"team":g["home_team"],"games_used":hn,"offense_epa_rating":round(ho,4),"defense_epa_rating":round(hd,4),"offense_rank":offense_rank.get(g["home_team"]),"defense_rank":defense_rank.get(g["home_team"]),"ranked_teams":len(eligible),"recent_form":team_form(g["home_team"])},
                        "away":{"team":g["away_team"],"games_used":an,"offense_epa_rating":round(ao,4),"defense_epa_rating":round(ad,4),"offense_rank":offense_rank.get(g["away_team"]),"defense_rank":defense_rank.get(g["away_team"]),"ranked_teams":len(eligible),"recent_form":team_form(g["away_team"])},
                        "estimated_home_advantage_points":1.5,
                        "scoring_edge_components":{"home_offense_vs_away_defense":round(45*(ho+ad),2),"away_offense_vs_home_defense":round(45*(ao+hd),2),"home_field_points":1.5},
                        "method":"Recency-weighted, opponent-adjusted EPA per play with shrinkage; recent form uses last five completed prior games."}})
    if not results: raise ValueError("Insufficient completed games for v2; do not publish")
    return {"model":"FOURTHDOWN v2","generated_at_utc":now.isoformat(),
            "season":season,"week":target_week,"status":"research_uncalibrated",
            "note":"Pregame EPA-only projections; no injuries, QB updates, live odds or calibrated win probabilities.",
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
    base=pbp.filter(pl.col("play_type").is_in(["pass","run"]) &
                    pl.col("epa").is_not_null() &
                    pl.col("posteam").is_not_null() &
                    pl.col("defteam").is_not_null())
    offense=base.group_by(["season","week","game_id","posteam"]).agg(pl.col("epa").mean().alias("offense_epa")).rename({"posteam":"team"})
    defense=base.group_by(["season","week","game_id","defteam"]).agg(pl.col("epa").mean().alias("defense_epa")).rename({"defteam":"team"})
    epa=offense.join(defense,on=["season","week","game_id","team"],how="inner").to_dicts()
    data=forecast(schedules,epa,now)
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
