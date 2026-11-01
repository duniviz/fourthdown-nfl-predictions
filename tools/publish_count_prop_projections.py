#!/usr/bin/env python3
"""Publish transparent, pregame count-prop projections. Never fabricate odds or picks."""
import argparse,csv,json,sys
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from backtest_count_props_walkforward import read_games,predict,MARKETS,number
from backtest_count_props_matchup_challenger import matchup_factor,usage_factor

MARKET_KEYS={"qb_completions":"player_pass_completions","rb_rush_attempts":"player_rush_attempts","wr_receptions":"player_receptions"}
def scheduled(path,season,week):
    teams={}
    with path.open(newline="",encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("season")!=str(season) or r.get("week")!=str(week) or r.get("game_type","REG")!="REG":continue
            home,away=r.get("home_team"),r.get("away_team")
            if home and away:
                teams[home]={"opponent":away,"game_id":r.get("game_id","")}
                teams[away]={"opponent":home,"game_id":r.get("game_id","")}
    if not teams:raise ValueError("No matching regular-season schedule")
    return teams
def generate(rows,schedule,season,week):
    games=read_games(rows); by_player=defaultdict(list); by_week=defaultdict(list)
    for (s,w,pid),r in games.items():
        if s==season and w<week:
            by_player[pid].append(r);by_week[(s,w)].append(r)
    for v in by_player.values():v.sort(key=lambda r:int(r["week"]))
    teams=scheduled(schedule,season,week);result=[]
    for pid,hist in by_player.items():
        last=hist[-1];team=last.get("recent_team") or last.get("team")
        if team not in teams:continue
        pos=last.get("position","").upper()
        for market,(position,field,opportunities) in MARKETS.items():
            if pos!=position:continue
            base=predict(hist,market,"candidate")
            if base is None:continue
            # Never apply a matchup adjustment against a missing/wrong opponent.
            current=dict(last,opponent_team=teams[team]["opponent"])
            prior_weeks=[(season,w) for w in range(1,week)]
            defense=matchup_factor(by_week,current,market,prior_weeks,.20 if market!="wr_receptions" else .10)
            usage=usage_factor(hist,current,market,by_week,.20 if market=="rb_rush_attempts" else (.10 if market=="wr_receptions" else 0))
            projected=round(max(0,base*defense*usage),1)
            recent=[number(r,field) for r in hist[-5:]]
            recent=[x for x in recent if x is not None]
            result.append({"player_id":pid,"player":last.get("player_display_name") or last.get("player_name") or pid,
                "team":team,"opponent":teams[team]["opponent"],"game_id":teams[team]["game_id"],
                "market_key":MARKET_KEYS[market],"projection":projected,
                "base_projection":round(base,2),"defense_factor":round(defense,4),
                "workload_factor":round(usage,4),"recent_5_avg":round(sum(recent)/len(recent),1) if recent else None,
                "games_used":len(hist),"model":"count_props_matchup_v1","last_week_used":int(last["week"]),
                "reason":"Recent volume and efficiency, adjusted for historical opponent position-group allowance and recent team role share where supported."})
    return {"status":"model_projections_not_betting_recommendations","season":season,"week":week,
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),"players":sorted(result,key=lambda x:(x["market_key"],x["player"]))}
def main():
    p=argparse.ArgumentParser();p.add_argument("--weekly-csv",type=Path,required=True)
    p.add_argument("--schedule-csv",type=Path,required=True);p.add_argument("--season",type=int,required=True)
    p.add_argument("--week",type=int,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    with a.weekly_csv.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
    out=generate(rows,a.schedule_csv,a.season,a.week)
    if not out["players"]:raise SystemExit("No count projections available; refusing empty publish")
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+"\n")
    print("Generated",len(out["players"]),"count prop projections for",a.season,a.week)
if __name__=="__main__":main()
