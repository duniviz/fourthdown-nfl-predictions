"""Publish transparent, pregame player yardage baselines (not betting picks).
Only completed prior weeks are used. No sportsbook odds or injury adjustments.
"""
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
try:
    import nflreadpy as nfl
except ModuleNotFoundError:  # lets pure projection helpers be unit tested locally
    nfl = None

METRICS = (
    ("passing_yards", "Passing yards", "attempts"),
    ("attempts", "Pass attempts", "attempts"),
    ("completions", "Pass completions", "attempts"),
    ("passing_tds", "Pass TDs", "attempts"),
    ("interceptions", "Interceptions", "attempts"),
    ("rushing_yards", "Rushing yards", "carries"),
    ("carries", "Rush attempts", "carries"),
    ("rushing_tds", "Rushing TDs", "carries"),
    ("receiving_yards", "Receiving yards", "targets"),
    ("receptions", "Receptions", "targets"),
    ("receiving_tds", "Receiving TDs", "targets"),
)

# Forecasting a stat and publishing a recommendation are deliberately separate.
# Count/TD forecasts remain research-only until their own archived calibration
# becomes available to the recommendation gate.
PRIOR_RATE = {
    "passing_yards": 6.6, "attempts": 1.0, "completions": .63,
    "passing_tds": .043, "interceptions": .022, "rushing_yards": 4.1,
    "carries": 1.0, "rushing_tds": .030, "receiving_yards": 7.0,
    "receptions": .64, "receiving_tds": .045,
}
PRIOR_OPPORTUNITIES = {
    "passing_yards": 70, "attempts": 70, "completions": 70,
    "passing_tds": 100, "interceptions": 100, "rushing_yards": 35,
    "carries": 35, "rushing_tds": 80, "receiving_yards": 25,
    "receptions": 25, "receiving_tds": 60,
}
MARKET_KEYS = {
    "passing_yards": "player_pass_yds", "attempts": "player_pass_attempts",
    "completions": "player_pass_completions", "passing_tds": "player_pass_tds",
    "interceptions": "player_pass_interceptions", "rushing_yards": "player_rush_yds",
    "carries": "player_rush_attempts", "rushing_tds": "player_rush_tds",
    "receiving_yards": "player_rec_yds", "receptions": "player_receptions",
    "receiving_tds": "player_rec_tds", "anytime_td": "player_anytime_td",
}
def num(x):
    try: return float(x or 0)
    except (TypeError, ValueError): return 0.0


def clamp(value, low, high):
    return max(low, min(high, value))

def load_game_context():
    """Read this run's published team forecast without requiring it."""
    try:
        payload=json.loads(Path("data/live-v2.json").read_text(encoding="utf-8"))
        return {(str(g.get("home")),str(g.get("away"))):g for g in payload.get("games",[])}
    except (OSError, ValueError, TypeError):
        return {}

def load_calibration():
    """Use only a sufficiently large, archived forecast sample."""
    try:
        rows=json.loads(Path("data/player-calibration.json").read_text(encoding="utf-8")).get("markets",[])
        return {str(row.get("stat_key")):row for row in rows}
    except (OSError, ValueError, TypeError):
        return {}

def load_learned_weights():
    try:
        rows=json.loads(Path("data/player-weight-learning.json").read_text(encoding="utf-8")).get("weights",{})
        return {k:clamp(float(v.get("weight",0)),0,1) for k,v in rows.items()}
    except (OSError,ValueError,TypeError,AttributeError):
        return {}

def game_script_multiplier(metric, team_margin):
    """Small, capped volume adjustment from the team's published score forecast."""
    if not math.isfinite(team_margin):
        return 1.0
    if metric=="rushing_yards":
        return round(1+clamp(team_margin*0.008,-0.06,0.06),4)
    # Passing and receiving volume get a modest boost for projected trailing teams.
    return round(1-clamp(team_margin*0.005,-0.04,0.04),4)

def project_yards(stats, metric, volume):
    """Volume x efficiency with regression and an uncertainty estimate.

    Avoid chasing short-term yardage spikes. This is a research forecast,
    not a calibrated sportsbook edge or a probability of covering a line.
    """
    recent=stats[-8:]
    opportunities=[max(0.0,num(r.get(volume))) for r in recent]
    yards=[max(0.0,num(r.get(metric))) for r in recent]
    weights=[0.88**(len(recent)-1-i) for i in range(len(recent))]
    wsum=sum(weights)
    weighted_volume=sum(w*v for w,v in zip(weights,opportunities))/wsum
    total_opp=sum(w*v for w,v in zip(weights,opportunities))
    total_yards=sum(w*y for w,y in zip(weights,yards))
    # Regularization dampens explosive small-sample efficiency outliers.
    prior_rate=PRIOR_RATE[metric]
    prior_opportunities=PRIOR_OPPORTUNITIES[metric]
    rate=(total_yards+prior_rate*prior_opportunities)/(total_opp+prior_opportunities)
    # Player's own season-long workload anchors the more recent workload.
    season_volume=sum(max(0,num(x.get(volume))) for x in stats)/len(stats)
    expected_volume=0.65*weighted_volume+0.35*season_volume
    forecast=max(0,expected_volume*rate)
    # Conservative shrinkage to player's season yards/game mean.
    season_mean=sum(max(0,num(x.get(metric))) for x in stats)/len(stats)
    forecast=0.8*forecast+0.2*season_mean
    deviations=[y-forecast for y in yards]
    spread=math.sqrt(sum(d*d for d in deviations)/max(1,len(deviations)))
    # Descriptive uncertainty only, not a calibrated prediction interval.
    return round(forecast,1),round(spread,1),round(expected_volume,1),round(rate,2)

def starter_qb_workload(records):
    """Estimate starter-level pass volume from full QB appearances, not relief games.

    This is a workload proxy, NOT independent confirmation of the named starter.
    Do not infer a starter from DraftKings lines.
    """
    ordered=sorted(records,key=lambda r:int(r["week"]))
    full=[max(0.0,num(r.get("attempts"))) for r in ordered if num(r.get("attempts"))>=20]
    if not full:
        return None
    recent=full[-5:]
    # Blend recent and season full-game averages; exclude relief appearances.
    return clamp(0.7*(sum(recent[-3:])/len(recent[-3:]))+0.3*(sum(full)/len(full)),15,55)

def generate():
    if nfl is None:
        raise RuntimeError("nflreadpy is required to generate player research")
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
    # Opponent adjustments use completed prior games only. Aggregate TEAM totals
    # rather than player appearances, and shrink small samples toward neutral.
    team_week=defaultdict(lambda:defaultdict(float))
    team_volume_week=defaultdict(lambda:defaultdict(float))
    defense_week=defaultdict(lambda:defaultdict(float))
    for (team,player),records in history.items():
        for record in records:
            key=(team,int(record["week"]))
            opp=str(record.get("opponent_team") or "")
            # Each opportunity column is counted once per player-game.
            # Several markets share attempts/carries/targets; counting each
            # market separately multiplies team workload and every projection.
            for volume in {volume for _,_,volume in METRICS}:
                team_volume_week[key][volume]+=max(0,num(record.get(volume)))
            for metric,_,_ in METRICS:
                team_week[key][metric]+=max(0,num(record.get(metric)))
                if opp:
                    defense_week[(opp,int(record["week"]))][metric]+=max(0,num(record.get(metric)))
    # Position-specific opponent totals, grouped by completed team-week.
    # Only three markets demonstrated lower MAE in both historical seasons.
    position_markets={("QB","passing_yards"),("RB","rushing_yards"),("RB","receiving_yards")}
    position_allowed=defaultdict(lambda:defaultdict(float))
    for (team,player),records in history.items():
        for record in records:
            pos=str(record.get("position") or "").upper()
            opp=str(record.get("opponent_team") or "")
            if not opp: continue
            for eligible_pos,metric in position_markets:
                if pos==eligible_pos:
                    position_allowed[(opp,int(record["week"]),pos)][metric]+=max(0,num(record.get(metric)))
    position_league={}
    position_defense={}
    for pos,metric in position_markets:
        values=[v[metric] for (opp,w,p),v in position_allowed.items() if p==pos]
        neutral=sum(values)/len(values) if values else 0
        position_league[(pos,metric)]=neutral
        for opponent in {k[0] for k in position_allowed}:
            samples=[v[metric] for (opp,w,p),v in sorted(position_allowed.items(),key=lambda item:item[0][1]) if opp==opponent and p==pos]
            position_defense[(opponent,pos,metric)]=samples[-5:] if samples else []
    league_mean={}
    defense_mean={}
    for metric,_,_ in METRICS:
        league_values=[v[metric] for v in team_week.values() if v[metric]>0]
        league_mean[metric]=sum(league_values)/len(league_values) if league_values else 1
        for team in {key[0] for key in defense_week}:
            vals=[v[metric] for key,v in defense_week.items() if key[0]==team and v[metric]>0]
            defense_mean[(team,metric)]=(sum(vals)/len(vals),len(vals)) if vals else (league_mean[metric],0)
    # Descriptive opponent rankings: rank 1 allows the FEWEST yards.
    # Based solely on completed games preceding the forecast week.
    defense_context={}
    for metric in ("passing_yards","rushing_yards","receiving_yards"):
        by_team={}
        for defense in {k[0] for k in defense_week}:
            games_allowed=sorted(((w,vals[metric]) for (t,w),vals in defense_week.items() if t==defense),key=lambda x:x[0])
            if games_allowed:
                by_team[defense]=games_allowed
        ranking=sorted(by_team,key=lambda t:sum(v for _,v in by_team[t])/len(by_team[t]))
        for rank,defense in enumerate(ranking,1):
            samples=by_team[defense]
            season_avg=sum(v for _,v in samples)/len(samples)
            recent=samples[-3:]
            defense_context[(defense,metric)]={
                "rank":rank,"ranked_teams":len(ranking),
                "season_allowed_per_game":round(season_avg,1),
                "last_3_allowed_per_game":round(sum(v for _,v in recent)/len(recent),1),
                "last_3_games":len(recent),
                "basis":"opponent team total yards allowed, not position-specific"
            }
    learned_weights=load_learned_weights()
    # Current official statuses exclude confirmed absences. Questionable is not treated as out.
    overrides={}
    try:
        current_injuries=json.loads(Path("data/injuries.json").read_text(encoding="utf-8"))
        for injury_team,payload in current_injuries.get("teams",{}).items():
            for item in payload.get("players",[]):
                name=str(item.get("player") or "").casefold()
                status=str(item.get("status") or "").lower()
                if name and status:
                    overrides[(str(injury_team),name)]=status
    except (OSError, ValueError, TypeError):
        pass
    # Availability overrides apply only to the exact verified game/week.
    # Never infer that a player is active from a missing injury report.
    verified=Path("data/verified-week7-injuries.json")
    if verified.exists() and season==2026 and week==7:
        snap=json.loads(verified.read_text(encoding="utf-8"))
        if snap.get("season")==season and snap.get("week")==week:
            for team,rows in snap.get("teams",{}).items():
                for name,position,status in rows:
                    overrides[(team,name.casefold())]=status.lower()
            # Confirmed IR and starting-QB news, scoped to this matchup only.
            overrides[("PHI","jalen hurts")]="out"
            overrides[("PHI","will shipley")]="out"
            overrides[("PHI","carson steele")]="out"
    # These files are generated earlier in the same workflow. Missing files fail open.
    game_context=load_game_context()
    calibration=load_calibration()
    results=[]
    for game in games:
        context=game_context.get((str(game["home_team"]),str(game["away_team"])),{})
        home_score=num(context.get("projected_home_score"))
        away_score=num(context.get("projected_away_score"))
        for team,opp in ((game["home_team"],game["away_team"]),(game["away_team"],game["home_team"])):
            team_margin=(home_score-away_score) if team==game["home_team"] else (away_score-home_score)
            # Forecast team opportunity totals before allocating player workloads.
            # Blend recent team play volume with season history; no future games.
            team_keys=sorted((k for k in team_volume_week if k[0]==team),key=lambda k:k[1])
            team_targets={}
            for metric,_,volume in METRICS:
                series=[team_volume_week[k][volume] for k in team_keys if team_volume_week[k][volume]>0]
                if series:
                    recent=series[-4:]
                    team_targets[volume]=0.65*sum(recent)/len(recent)+0.35*sum(series)/len(series)
            # Fail closed if input aggregation or source schema creates
            # impossible per-game team workloads. Never publish false edges.
            hard_max={"attempts":80.0,"carries":65.0,"targets":85.0}
            for volume,cap in hard_max.items():
                if team_targets.get(volume,0)>cap:
                    raise ValueError(f"Implausible {team} team {volume}: {team_targets[volume]:.1f} > {cap}; refusing player projections")
            # Each player's raw expected share is reconciled to the team total.
            allocation={}
            for metric,_,volume in METRICS:
                eligible=[]
                for (t,pid),records in history.items():
                    if t!=team or len(records)<1: continue
                    if overrides.get((team,str(records[-1].get("player_display_name") or records[-1].get("player_name") or "").casefold())) in ("out","inactive","ir"): continue
                    recent=sorted(records,key=lambda x:int(x["week"]))[-5:]
                    last_week=int(recent[-1]["week"])
                    # Do not automatically reallocate to long-inactive players.
                    if week-last_week>2: continue
                    vol=[max(0,num(x.get(volume))) for x in recent]
                    raw=0.7*sum(vol[-3:])/len(vol[-3:])+0.3*sum(vol)/len(vol)
                    if raw>0: eligible.append((pid,raw))
                total=sum(v for _,v in eligible)
                target=team_targets.get(volume)
                for pid,raw in eligible:
                    allocation[(pid,metric)]=target*raw/total if total>0 and target is not None else raw
            for (t,player),stats in history.items():
                if t!=team: continue
                stats=sorted(stats,key=lambda x:int(x["week"]))
                if len(stats)<1 or week-int(stats[-1]["week"])>2: continue
                player_name=str(stats[-1].get("player_display_name") or stats[-1].get("player_name") or player)
                availability=overrides.get((team,player_name.casefold()),"unconfirmed")
                if availability in ("out","inactive","ir"): continue
                for metric,label,volume in METRICS:
                    last=stats[-5:]
                    values=[num(x.get(metric)) for x in last]
                    avg=sum(values)/len(values)
                    # Eligibility follows meaningful recent opportunity, not a high yardage cutoff.\n                    # Include backups and secondary receivers while excluding zero-role players.\n                    if max(num(x.get(volume)) for x in last)<(8 if metric=="passing_yards" else 2): continue
                    v=[num(x.get(volume)) for x in last]
                    # Opponent allowed yards per player appearance is descriptive, not
                    # position-adjusted; do not use it as an unvalidated multiplier.
                    opp_values=opponents[opp][metric]
                    baseline,uncertainty,expected_volume,expected_rate=project_yards(stats,metric,volume)
                    # Team-consistent workload allocation; conservative defensive
                    # adjustment (capped ±10%, shrunk by observed games).
                    allocated=allocation.get((player,metric))
                    if allocated is None: continue
                    adjusted=0.75*allocated+0.25*expected_volume
                    # For a QB with established full-game passing volume, avoid
                    # splitting his starter workload with a backup's recent starts.
                    # Preserve every eligible player's record; never drop backups.
                    qb_full_game_volume=starter_qb_workload(stats) if str(stats[-1].get("position") or "").upper()=="QB" and volume=="attempts" else None
                    if qb_full_game_volume is not None:
                        adjusted=0.85*qb_full_game_volume+0.15*expected_volume
                    # A newly elevated player with fewer than three observed
                    # games cannot be assumed to absorb the entire missing
                    # teammate workload without an independently verified role.
                    # Cap extrapolation at 20% above their observed carry/target
                    # workload until at least three games establish the role.
                    limited_sample=len(stats)<3
                    if limited_sample:
                        observed=sum(max(0,num(x.get(volume))) for x in stats)/len(stats)
                        adjusted=min(adjusted,observed*1.20)
                    defensive_avg,def_games=defense_mean.get((opp,metric),(league_mean[metric],0))
                    ratio=defensive_avg/max(1,league_mean[metric])
                    adjustment=1+min(0.10,max(-0.10,(ratio-1)*0.30*def_games/(def_games+6)))
                    position=str(stats[-1].get("position") or "").upper()
                    if (position,metric) in position_markets:
                        samples=position_defense.get((opp,position,metric),[])
                        neutral=position_league.get((position,metric),0)
                        if len(samples)>=3 and neutral>0:
                            observed=sum(samples)/len(samples)
                            factor=(observed+5*neutral)/(6*neutral)
                            adjustment=clamp(factor,0.90,1.10)
                        else:
                            adjustment=1.0
                    # Full-game QB workload is an individual conditional starter
                    # forecast, not a simultaneous share of the team's passing.
                    # A value >1 signals competing QB scenarios or mismatched
                    # team baseline, not an impossible QB passing-yard forecast.
                    raw_role_share=adjusted/max(0.1,team_targets.get(volume,adjusted))
                    role_share=clamp(raw_role_share,0.0,1.0) if position=="QB" and volume=="attempts" and qb_full_game_volume is not None else raw_role_share
                    script_multiplier=game_script_multiplier(metric,team_margin)
                    calibrated=calibration.get(metric,{})
                    calibration_n=int(calibrated.get("sample_size",0) or 0)
                    # A bias correction is deliberately dormant until 40 archived forecasts
                    # establish a stable market-level direction.
                    calibration_bias=clamp(num(calibrated.get("mean_error")), -5.0, 5.0)*learned_weights.get(metric,0.0) if calibration_n>=40 else 0.0
                    baseline=round(max(0,baseline*adjusted/max(0.1,expected_volume)*adjustment*script_multiplier+calibration_bias),1)
                    # Explicit RB workload scenarios when a listed starting RB
                    # is questionable. Never treat "questionable" as "out".
                    scenario=None
                    if metric=="rushing_yards" and team=="PHI" and player_name.casefold()=="dameon pierce" and overrides.get(("PHI","saquon barkley"))=="questionable":
                        # Barkley fully active: backup gets only a modest
                        # fraction of recent carries. Limited: intermediate.
                        # Out: reallocated carries, but still cap speculative
                        # workload growth for a player with <3 observations.
                        recent_carries=sum(max(0,num(x.get("carries"))) for x in stats[-3:])/min(3,len(stats))
                        full_carries=min(adjusted,recent_carries*0.45)
                        limited_carries=min(adjusted,recent_carries*0.80)
                        out_carries=adjusted
                        yard_per_carry=baseline/max(0.1,adjusted)
                        scenario={
                            "trigger_player":"Saquon Barkley",
                            "trigger_status":"questionable",
                            "note":"Conditional research scenarios, not verified snap-share forecasts. Do not rank as a confirmed betting edge until starter availability and role are verified.",
                            "full_go":{"carries":round(full_carries,1),"projection":round(full_carries*yard_per_carry,1)},
                            "limited":{"carries":round(limited_carries,1),"projection":round(limited_carries*yard_per_carry,1)},
                            "out":{"carries":round(out_carries,1),"projection":round(out_carries*yard_per_carry,1)}
                        }
                        # Default to the conservative active-starter scenario
                        # until a verified inactive designation arrives.
                        adjusted=full_carries
                        baseline=scenario["full_go"]["projection"]
                    results.append({
                        "game_id":str(game["game_id"]),"team":team,"opponent":opp,
                        "player_id":player,
                        "espn_athlete_id":espn_ids.get(player),
                        "player":stats[-1].get("player_display_name") or stats[-1].get("player_name") or player,
                        "position":stats[-1].get("position"),
                        "market":label,"stat_key":metric,"market_key":MARKET_KEYS[metric],"games_used":len(stats),
                        "sample_warning":"Limited current-season games; projected workload capped at 120% of observed opportunities" if len(stats)<3 else None,
                        "bet_recommendation":False,
                        "last_5":[round(x,1) for x in values],
                        "last_5_avg":round(avg,1),
                        "last_3_avg":round(sum(values[-3:])/min(3,len(values)),1),
                        "last_5_opportunities_avg":round(sum(v)/len(v),1),
                        "opportunity_type":volume,
                        "opponent_player_appearance_avg":round(sum(opp_values)/len(opp_values),1) if len(opp_values)>=10 else None,
                        "projection":baseline,
                        "injury_scenarios":scenario,
                        "uncertainty_yards":uncertainty,
                        "uncertainty":uncertainty,
                        "expected_opportunities":round(adjusted,1),
                        "qb_full_game_workload":round(qb_full_game_volume,1) if qb_full_game_volume is not None else None,
                        "qb_raw_team_share":round(raw_role_share,3) if qb_full_game_volume is not None else None,
                        "qb_workload_method":"established_full_game_appearances_not_verified_starter" if qb_full_game_volume is not None else None,
                        "opponent_adjustment":round(adjustment,3),
                        "opponent_defense_context":defense_context.get((opp,metric)),
                        "opponent_position_context":({"games":len(position_defense.get((opp,position,metric),[])),"last_5_allowed_per_game":round(sum(position_defense[(opp,position,metric)])/len(position_defense[(opp,position,metric)]),1)} if (position,metric) in position_markets and position_defense.get((opp,position,metric)) else None),
                        "game_script_adjustment":script_multiplier,
                        "calibration_bias_yards":round(calibration_bias,2),
                        "learned_bias_weight":learned_weights.get(metric,0.0),
                        "calibration_sample_size":calibration_n,
                        "role_share":round(role_share,3),
                        "committee_risk":"high" if metric=="rushing_yards" and role_share<0.30 else ("moderate" if metric=="rushing_yards" and role_share<0.48 else "low"),
                        "availability_status":availability,
                        "team_opportunity_allocation":True,
                        "expected_yards_per_opportunity":expected_rate,
                        "method":"Team-volume and teammate-share allocation, recency-weighted player efficiency, season shrinkage, capped opponent and game-script adjustments; calibration bias applies only after 40 archived forecasts",
                        "bet_recommendation":False,
                    })
    # A player's anytime-TD chance is derived only from this model's rushing
    # and receiving TD rate forecasts.  It is a probability research field,
    # not an invented O/U line, and is matched only to a verified DK anytime
    # market by the client.
    touchdown_rates={}
    for row in results:
        if row["stat_key"] in ("rushing_tds", "receiving_tds"):
            key=(row["game_id"],row["player_id"])
            touchdown_rates.setdefault(key, []).append(row)
    for pair, rows_for_player in touchdown_rates.items():
        rate=sum(max(0,float(x["projection"])) for x in rows_for_player)
        probability=1-math.exp(-rate)
        source=rows_for_player[0]
        results.append({
            "game_id":source["game_id"],"team":source["team"],"opponent":source["opponent"],
            "player_id":source["player_id"],"espn_athlete_id":source["espn_athlete_id"],
            "player":source["player"],"position":source["position"],"market":"Anytime TD",
            "stat_key":"anytime_td","market_key":MARKET_KEYS["anytime_td"],"games_used":source["games_used"],
            "projection":round(probability*100,1),"projection_probability":round(probability,4),
            "last_5":None,"last_5_avg":None,"last_3_avg":None,"injury_scenarios":None,
            "availability_status":source["availability_status"],"bet_recommendation":False,
            "method":"Derived from the model's rushing and receiving TD-rate forecasts; independent-event approximation; research only.",
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
    print(f"Published {len(results)} player baselines across {len(games)} games for week {week}")

if __name__=="__main__": generate()
