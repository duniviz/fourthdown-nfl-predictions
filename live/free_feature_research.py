"""Collect free nflverse features for future leak-free challenger evaluation.

Research-only: feature presence never changes production predictions by itself.
Only completed prior-week games may contribute to a target week.
"""
import json
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import nflreadpy as nfl

def safe_rows(loader,season):
    try: return loader([season]).to_dicts()
    except Exception as exc:
        print(f"Optional nflverse source unavailable: {exc}")
        return []

def aggregate_pbp(rows,season,target_week):
    by_team=defaultdict(lambda:defaultdict(list))
    for r in rows:
        try:
            if int(r.get("season"))!=season or int(r.get("week"))>=target_week:continue
            team=r.get("posteam")
            if not team or r.get("season_type") not in ("REG",None):continue
            week=int(r["week"])
        except (TypeError,ValueError):continue
        if r.get("play_type") not in ("pass","run"):continue
        key=(team,week)
        by_team[key]["plays"].append(1)
        for name,field in (("epa","epa"),("success","success"),("yards_gained","yards_gained")):
            try:
                value=float(r.get(field))
                if abs(value)<10000:by_team[key][name].append(value)
            except (TypeError,ValueError):pass
        if r.get("yardline_100") is not None:
            try:
                if float(r["yardline_100"])<=20:by_team[key]["redzone_plays"].append(1)
            except (TypeError,ValueError):pass
        if r.get("play_type")=="pass":by_team[key]["pass_plays"].append(1)
    return by_team

def summarize(by_team):
    output={}
    teams={t for t,w in by_team}
    for team in sorted(teams):
        games=sorted((w,v) for (t,w),v in by_team.items() if t==team)[-5:]
        def values(k):return [x for _,v in games for x in v[k]]
        plays=len(values("plays"))
        if not plays:continue
        output[team]={"games":len(games),"plays_per_game":round(plays/len(games),2),
          "neutral_pass_proxy":round(len(values("pass_plays"))/plays,3),
          "epa_per_play":round(sum(values("epa"))/len(values("epa")),3) if values("epa") else None,
          "success_rate":round(sum(values("success"))/len(values("success")),3) if values("success") else None,
          "redzone_plays_per_game":round(len(values("redzone_plays"))/len(games),2)}
    return output

def main():
    now=datetime.now(timezone.utc)
    season=now.year if now.month>=3 else now.year-1
    schedules=safe_rows(nfl.load_schedules,season)
    upcoming=[int(g["week"]) for g in schedules if g.get("game_type")=="REG"
       and g.get("home_score") is None and g.get("away_score") is None]
    if not upcoming:
        print("No future week to evaluate; research feature refresh skipped")
        return
    target_week=min(upcoming)
    pbp=safe_rows(nfl.load_pbp,season)
    snaps=safe_rows(nfl.load_snap_counts,season)
    ngs=safe_rows(nfl.load_nextgen_stats,season)
    # NGS and snap-count data may be delayed or inconsistent; count only,
    # do not promote into production without historical availability tests.
    report={"generated_at_utc":now.isoformat(),"season":season,"target_week":target_week,
      "status":"research_only_no_automatic_promotion",
      "features":summarize(aggregate_pbp(pbp,season,target_week)),
      "source_counts":{"pbp":len(pbp),"snap_counts":len(snaps),"nextgen_stats":len(ngs)},
      "caveats":["No current-week results used","Pass-play ratio is not neutral-script pass rate",
                 "Snap counts and NGS collected for availability checks, not yet model inputs",
                 "Player and team scores are not yet reconciled in a joint simulation"]}
    Path("data/free-feature-research.json").write_text(json.dumps(report,indent=2)+"\n")
    print("Saved research features for",len(report["features"]),"teams")

if __name__=="__main__":main()
