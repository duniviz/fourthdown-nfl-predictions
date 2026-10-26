"""Pregame injury adjustment: replacement-based QB estimate with baseline correction.

The base EPA model already includes recent QB performances. We adjust only
for the expected QB vs the mix of QBs in those games. Other injuries are
tracked but not given fabricated numerical effects. This is exploratory.
"""
from collections import defaultdict
import math

OUT_WORDS=("injured reserve","inactive","ruled out","out for season","season-ending","out indefinitely","suspended","physically unable","reserve/injured")
def confirmed_out(status):
    s=str(status or "").lower().strip()
    return s=="out" or s=="ir" or any(word in s for word in OUT_WORDS)

def normalize(s):
    return " ".join(str(s or "").lower().replace(".","").split())

def _num(x):
    try:
        v=float(x or 0)
        return v if math.isfinite(v) else 0.
    except (ValueError,TypeError):return 0.

def estimate(team, injury_rows, weekly_stats, schedules, target_week):
    reported=[r for r in injury_rows if confirmed_out(r.get("status"))]
    base={"points":0.,"status":"no_confirmed_out_in_feed" if not reported else "insufficient_verified_replacement_data",
          "players":[],"reported_out":len(reported),"unmodeled_injuries":[
              {"player":r.get("player"),"position":r.get("position"),"status":r.get("status")}
              for r in reported if str(r.get("position","")).upper()!="QB"]}
    if not reported:return base
    # Only completed earlier games, never future participation.
    weeks=set()
    for g in schedules:
        if g.get("game_type")!="REG":continue
        try:w=int(g.get("week"))
        except (ValueError,TypeError):continue
        if w>=target_week:continue
        if (g.get("home_team")==team and g.get("home_score") is not None and g.get("away_score") is not None) or (g.get("away_team")==team and g.get("home_score") is not None and g.get("away_score") is not None):
            weeks.add(w)
    if len(weeks)<3:return base
    # Compare team passing production by QB from weekly stats, with conservative
    # shrinkage and no arbitrary injury penalty. Attempts identify actual QB use.
    by_player=defaultdict(list)
    by_week=defaultdict(list)
    for r in weekly_stats:
        if r.get("team")!=team or str(r.get("position","")).upper()!="QB":continue
        try:w=int(r.get("week"))
        except (TypeError,ValueError):continue
        if w not in weeks:continue
        attempts=_num(r.get("attempts"))
        if attempts<8:continue
        name=normalize(r.get("player_display_name") or r.get("player_name"))
        if not name:continue
        # NFL weekly stats expose passing_yards, passing_tds, interceptions,
        # rushing_yards. This proxy is NOT a causal QB valuation.
        efficiency=(_num(r.get("passing_yards"))+_num(r.get("rushing_yards"))
                    +20*_num(r.get("passing_tds"))-35*_num(r.get("interceptions")))/max(attempts,1)
        efficiency=max(-2,min(15,efficiency))
        by_player[name].append((w,efficiency,attempts))
        by_week[w].append((name,efficiency,attempts))
    absent_qbs=[r for r in reported if str(r.get("position","")).upper()=="QB"]
    if not absent_qbs:return base
    absent_names={normalize(r.get("player")) for r in absent_qbs}
    # Need an observed alternative QB with >=2 distinct prior appearances;
    # do not assume an unnamed replacement or assign a guessed starter.
    candidates=[(name,vals) for name,vals in by_player.items()
                if name not in absent_names and len({w for w,_,_ in vals})>=2]
    if len(candidates)!=1:
        base["status"]="replacement_not_confirmed" if candidates else "replacement_sample_unavailable"
        return base
    replacement,vals=candidates[0]
    replacement_rating=sum(v*a for _,v,a in vals)/sum(a for _,v,a in vals)
    # Match the four-week half-life used in the team EPA baseline. An existing
    # replacement-heavy sample naturally produces a small incremental effect.
    weighted=[]
    for w,items in by_week.items():
        weight=2**(-(target_week-w-1)/4.)
        total_attempts=sum(a for _,_,a in items)
        if total_attempts:
            weighted.append((weight,sum(v*a for _,v,a in items)/total_attempts))
    if not weighted:return base
    baseline=sum(w*v for w,v in weighted)/sum(w for w,_ in weighted)
    # 0.45 point per efficiency-proxy unit is an uncalibrated provisional
    # coefficient; cap to +/- 2 points pending historical walk-forward fitting.
    adjustment=max(-2.,min(2.,(replacement_rating-baseline)*0.45))
    base.update({"points":round(adjustment,2),"status":"experimental_qb_baseline_adjustment",
        "players":[{"player":replacement,"role":"observed_replacement_candidate",
                    "games":len({w for w,_,_ in vals}),"adjustment_points":round(adjustment,2)}],
        "method":"Expected replacement proxy minus recency-weighted QB baseline; coefficient not backtested",
        "confidence":"low"})
    return base
