"""Walk-forward NFL player-yardage backtest: 2024 tune and 2025 holdout.
Run: python -m live.backtest_players
Only prior weeks enter each prediction; identical player/week cohorts for both models.
"""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
import nflreadpy as nfl
from live.player_research import METRICS, num, project_yards

def old_model(stats, metric):
    vals=[max(0,num(r.get(metric))) for r in stats[-5:]]
    return .55*sum(vals[-3:])/len(vals[-3:])+.45*sum(vals)/len(vals)

def backtest(seasons=(2024,2025)):
    rows=[]
    for season in seasons:
        raw=nfl.load_player_stats([season],summary_level="week").to_dicts()
        weeks=defaultdict(list)
        for r in raw:
            try: w=int(r["week"])
            except (ValueError,TypeError,KeyError): continue
            if str(r.get("season_type","REG")).upper() not in ("REG","2"): continue
            if w<1 or w>18 or not r.get("player_id") or not r.get("team"): continue
            weeks[w].append(r)
        history=defaultdict(list)
        for week in sorted(weeks):
            if week>=4:
                team_week=defaultdict(lambda:defaultdict(float))
                defense_week=defaultdict(lambda:defaultdict(float))
                for (team,pid),past in history.items():
                    for r in past:
                        key=(team,int(r["week"]))
                        for volume in {volume for _,_,volume in METRICS}:
                            team_week[key][volume]+=max(0,num(r.get(volume)))
                        for metric,_,_ in METRICS:
                            if r.get("opponent_team"):
                                defense_week[(r["opponent_team"],int(r["week"]))][metric]+=max(0,num(r.get(metric)))
                league={}
                for metric,_,_ in METRICS:
                    vals=[v[metric] for v in defense_week.values() if v[metric]>0]
                    league[metric]=sum(vals)/len(vals) if vals else 1
                for actual in weeks[week]:
                    team=str(actual["team"]); pid=str(actual["player_id"])
                    past=history.get((team,pid),[])
                    if len(past)<3 or week-int(past[-1]["week"])>2: continue
                    opp=str(actual.get("opponent_team") or "")
                    for metric,label,volume in METRICS:
                        last=past[-5:]
                        avg=sum(num(r.get(metric)) for r in last)/len(last)
                        if avg<(85 if metric=="passing_yards" else 18): continue
                        raw_pred,_,expected_volume,_=project_yards(past,metric,volume)
                        team_keys=sorted((k for k in team_week if k[0]==team),key=lambda k:k[1])
                        series=[team_week[k][volume] for k in team_keys if team_week[k][volume]>0]
                        if not series: continue
                        target=.65*sum(series[-4:])/len(series[-4:])+.35*sum(series)/len(series)
                        eligible=[]
                        for (t,p),records in history.items():
                            if t!=team or len(records)<3 or week-int(records[-1]["week"])>2: continue
                            rec=records[-5:]
                            volumes=[max(0,num(x.get(volume))) for x in rec]
                            v=.7*sum(volumes[-3:])/len(volumes[-3:])+.3*sum(volumes)/len(volumes)
                            if v>0: eligible.append((p,v))
                        total=sum(v for _,v in eligible)
                        player_vol=next((v for p,v in eligible if p==pid),0)
                        if total<=0 or player_vol<=0: continue
                        allocated=target*player_vol/total
                        adjusted=.75*allocated+.25*expected_volume
                        opp_vals=[v[metric] for k,v in defense_week.items() if k[0]==opp and v[metric]>0]
                        def_avg=sum(opp_vals)/len(opp_vals) if opp_vals else league[metric]
                        ratio=def_avg/max(1,league[metric])
                        adj=1+min(.10,max(-.10,(ratio-1)*.30*len(opp_vals)/(len(opp_vals)+6)))
                        new_pred=max(0,raw_pred*adjusted/max(.1,expected_volume)*adj)
                        # Pregame-only challenger signals, not used in the incumbent forecast.
                        vols=[max(0,num(x.get(volume))) for x in past[-8:]]
                        recent_vol=sum(vols[-3:])/len(vols[-3:])
                        full_vol=sum(vols)/len(vols)
                        opportunity_signal=max(-0.35,min(0.35,recent_vol/max(1,full_vol)-1))
                        defense_signal=max(-0.35,min(0.35,ratio-1))*len(opp_vals)/(len(opp_vals)+6)
                        old_pred=old_model(past,metric)
                        actual_yards=max(0,num(actual.get(metric)))
                        rows.append(dict(season=season,week=week,player_id=pid,player=actual.get("player_display_name") or pid,team=team,opponent=opp,market=metric,actual=round(actual_yards,1),old=round(old_pred,1),new=round(new_pred,1),opportunity_signal=round(opportunity_signal,6),defense_signal=round(defense_signal,6),old_abs_error=round(abs(old_pred-actual_yards),2),new_abs_error=round(abs(new_pred-actual_yards),2)))
            for r in weeks[week]:
                history[(str(r["team"]),str(r["player_id"]))].append(r)
    return rows

def summarize(rows):
    result=[]
    for season in (2024,2025):
        for metric,_,_ in METRICS:
            subset=[r for r in rows if r["season"]==season and r["market"]==metric]
            if not subset: continue
            old=sum(r["old_abs_error"] for r in subset)/len(subset)
            new=sum(r["new_abs_error"] for r in subset)/len(subset)
            result.append(dict(season=season,market=metric,samples=len(subset),old_mae=round(old,2),new_mae=round(new,2),improvement_pct=round((old-new)/old*100,2) if old else None,better="new" if new<old else "old"))
    return result

def main():
    rows=backtest()
    if not rows: raise RuntimeError("No predictions graded; verify historical player stats")
    out=Path("data/backtests");out.mkdir(parents=True,exist_ok=True)
    with (out/"player-predictions.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary=summarize(rows)
    (out/"player-summary.json").write_text(json.dumps({"method":"walk-forward; 2024 development / 2025 untouched holdout; no market odds","summary":summary},indent=2)+"\n")
    print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
