"""Conservative injury-aware score adjustments from prior team games.

Only confirmed OUT/IR reports can trigger an adjustment. No invented per-position
point penalties. When there is insufficient historical evidence, report unadjusted.
"""
from collections import defaultdict
from math import isfinite

OUT_WORDS=("injured reserve","inactive","ruled out","out for season","season-ending","out indefinitely","suspended","physically unable")
def confirmed_out(status):
    s=str(status or "").lower().strip()
    return s=="out" or any(word in s for word in OUT_WORDS)

def normalize(s):
    return " ".join(str(s or "").lower().replace(".","").split())

def estimate(team, injury_rows, weekly_stats, schedules, target_week):
    """Compare points scored with vs without each reported absent player.

    Requires at least two distinct prior team games in each group. Historical
    participation is inferred only from recorded weekly stats, so this supports
    skill players with recorded statistics; absence of stats does NOT prove
    injury or inactivity. We require positive recorded activity in comparison
    weeks and flag this method as exploratory.
    """
    reported=[r for r in injury_rows if confirmed_out(r.get("status"))]
    if not reported:return {"points":0.0,"status":"no_confirmed_out_in_feed","players":[]}
    completed={}
    for g in schedules:
        if g.get("game_type")!="REG" or int(g.get("week") or 0)>=target_week:continue
        w=int(g["week"])
        if g.get("home_team")==team and g.get("home_score") is not None:
            completed[w]=float(g["home_score"])
        elif g.get("away_team")==team and g.get("away_score") is not None:
            completed[w]=float(g["away_score"])
    by_name=defaultdict(set)
    for r in weekly_stats:
        if r.get("team")!=team:continue
        try:w=int(r.get("week"))
        except (TypeError,ValueError):continue
        if w not in completed:continue
        name=normalize(r.get("player_display_name") or r.get("player_name"))
        if not name:continue
        # Weekly rows may exist with zero touches; only use observable involvement.
        if sum(float(r.get(k) or 0) for k in ("attempts","carries","targets"))>0:
            by_name[name].add(w)
    candidates=[]
    for injury in reported:
        name=normalize(injury.get("player"))
        present=by_name.get(name,set()) & set(completed)
        absent=set(completed)-present
        if len(present)<2 or len(absent)<2:continue
        with_avg=sum(completed[w] for w in present)/len(present)
        without_avg=sum(completed[w] for w in absent)/len(absent)
        # A player absent from a box score may have been active but unused;
        # only accept the split for quarterbacks with meaningful attempts.
        if str(injury.get("position","")).upper()!="QB":continue
        raw=without_avg-with_avg
        # Strong shrinkage; observational, not causal. Guard extreme samples.
        adjustment=max(-6,min(6,raw*0.35))
        candidates.append({"player":injury.get("player"),"position":"QB","points":round(adjustment,2),
                           "games_with":len(present),"games_without":len(absent)})
    if not candidates:
        return {"points":0.0,"status":"insufficient_verified_player_splits","players":[],
                "reported_out":len(reported)}
    # One QB adjustment per team, avoid stacking multiple absences.
    best=max(candidates,key=lambda x:x["games_with"]+x["games_without"])
    return {"points":best["points"],"status":"experimental_qb_split","players":[best],
            "reported_out":len(reported)}
