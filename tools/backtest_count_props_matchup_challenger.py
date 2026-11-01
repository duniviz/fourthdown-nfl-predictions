#!/usr/bin/env python3
"""Strictly pregame count-prop matchup/usage challenger; research only.

Uses nflverse weekly box scores: player workload, target share, opponent
position-group counts allowed. No snap/route, weather, or bookmaker data is
assumed. Compares on IDENTICAL observed player-games with the original model.
"""
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from backtest_count_props_walkforward import MARKETS, read_games, predict, number

def mean(a):
    return sum(a)/len(a) if a else None

def build(rows):
    games=read_games(rows)
    by_player=defaultdict(list)
    by_week=defaultdict(list)
    for (season,week,pid),r in games.items():
        by_player[(season,pid)].append(r)
        by_week[(season,week)].append(r)
    for v in by_player.values():
        v.sort(key=lambda r:int(r["week"]))
    return by_player,by_week

def matchup_factor(week_rows, current, market, history_weeks, strength):
    """Defense vs QB completions / RB carries / WR catches, shrunk and capped.

    Only weeks strictly preceding prediction week; normalized to league-wide
    team-game allowed values so defensive schedule is partially controlled.
    """
    pos,field,_=MARKETS[market]
    opponent=(current.get("opponent_team") or "").strip()
    if not opponent:
        return 1.0
    defense=defaultdict(float)
    games=set()
    for w in history_weeks:
        for r in week_rows.get(w,[]):
            if r.get("position","").upper()!=pos:
                continue
            opp=(r.get("opponent_team") or "").strip()
            team=(r.get("recent_team") or r.get("team") or "").strip()
            if not opp or not team:
                continue
            v=number(r,field)
            if v is None:
                continue
            defense[(w[1],opp)]+=v
            games.add((w[1],opp))
    own=[v for (wk,opp),v in defense.items() if opp==opponent]
    all_values=list(defense.values())
    if len(own)<3 or len(all_values)<30:
        return 1.0
    league=mean(all_values)
    if not league or league<=0:
        return 1.0
    ratio=mean(own)/league
    reliability=len(own)/(len(own)+6)
    return max(.88,min(1.12,1+strength*reliability*(ratio-1)))

def usage_factor(player_history, current, market, by_week, strength):
    """Optional role share trend based only on team box scores, not future games."""
    pos,field,opps=MARKETS[market]
    if market=="qb_completions":
        return 1.0  # completion efficiency already modeled from attempts
    team=current.get("recent_team") or current.get("team")
    if not team:
        return 1.0
    shares=[]
    for r in player_history:
        w=(int(r["season"]),int(r["week"]))
        rteam=r.get("recent_team") or r.get("team")
        if rteam!=team:
            continue
        total=sum(number(p,field) or 0 for p in by_week.get(w,[]) if
                  (p.get("recent_team") or p.get("team"))==team and
                  p.get("position","").upper()==pos)
        own=number(r,field)
        if total>0 and own is not None:
            shares.append(own/total)
    if len(shares)<4:
        return 1.0
    long=mean(shares)
    recent=mean(shares[-3:])
    if not long or long<=0:
        return 1.0
    return max(.9,min(1.1,1+strength*(recent/long-1)))

def evaluate(rows,seasons,through_week):
    by_player,by_week=build(rows)
    errors=defaultdict(list)
    weekly=defaultdict(lambda:defaultdict(int))
    for (season,pid),player_rows in by_player.items():
        if season not in seasons:
            continue
        for current in player_rows:
            week=int(current["week"])
            if week>through_week:
                continue
            prior=[r for r in player_rows if int(r["week"])<week]
            earlier=[(season,w) for w in range(1,week)]
            for market,(pos,field,_) in MARKETS.items():
                if current.get("position","").upper()!=pos:
                    continue
                actual=number(current,field)
                base=predict(prior,market,"candidate")
                if actual is None or base is None:
                    continue
                # Hold identical samples for every challenger variant.
                variants={"current":base}
                for name,defense_strength,usage_strength in (
                    ("defense",.20,0),("usage",0,.20),
                    ("combined",.20,.20),("conservative",.10,.10)):
                    defense=matchup_factor(by_week,current,market,earlier,defense_strength) if defense_strength else 1
                    usage=usage_factor(prior,current,market,by_week,usage_strength) if usage_strength else 1
                    variants[name]=max(0,base*defense*usage)
                for name,estimate in variants.items():
                    errors[(market,name)].append(estimate-actual)
                weekly[f"{season}-W{week}"][market]+=1
    summary={}
    for market in MARKETS:
        summary[market]={}
        for variant in ("current","defense","usage","combined","conservative"):
            e=errors[(market,variant)]
            n=len(e)
            summary[market][variant]={"samples":n,
                "mae":round(mean([abs(x) for x in e]),3) if n else None,
                "rmse":round(math.sqrt(mean([x*x for x in e])),3) if n else None,
                "bias":round(mean(e),3) if n else None}
        base=summary[market]["current"]
        summary[market]["winners"]=[name for name in ("defense","usage","combined","conservative")
            if base["samples"]>=100 and summary[market][name]["mae"]<base["mae"]
            and summary[market][name]["rmse"]<base["rmse"]]
    return {"status":"research_only_not_promoted","seasons":sorted(seasons),
        "through_week":through_week,"markets":summary,"weekly_samples":dict(weekly),
        "caveats":"Historical observed players only. Defensive position allowed is not adjusted for opposing offenses or injury. No snap share, routes, pregame spread, sportsbook calibration or live availability. All factors strictly prior week."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--weekly-csv",type=Path,required=True)
    p.add_argument("--seasons",type=int,nargs="+",default=[2024,2025,2026])
    p.add_argument("--through-week",type=int,default=18)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    with a.weekly_csv.open(newline="",encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    result=evaluate(rows,set(a.seasons),a.through_week)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result["markets"],indent=2))
if __name__=="__main__":
    main()
