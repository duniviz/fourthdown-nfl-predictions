"""Leakage-safe walk-forward score distribution evaluation of game simulator.

Uses only previously completed regular-season games to forecast team scores.
No player props, betting lines, or production outputs are changed.
"""
import argparse,json,math
from collections import defaultdict
from pathlib import Path
import nflreadpy as nfl
from tools.correlated_game_sim import simulate

def score_metrics(predictions):
    n=len(predictions)
    if not n:return {"games":0}
    return {"games":n,
        "home_mae":round(sum(abs(r["home_pred"]-r["home_actual"]) for r in predictions)/n,3),
        "away_mae":round(sum(abs(r["away_pred"]-r["away_actual"]) for r in predictions)/n,3),
        "total_mae":round(sum(abs(r["total_pred"]-r["total_actual"]) for r in predictions)/n,3),
        "total_80pct_interval_coverage":round(sum(r["total_lo"]<=r["total_actual"]<=r["total_hi"] for r in predictions)/n,4),
        "winner_brier":round(sum((r["home_win_prob"]-r["home_win"])**2 for r in predictions)/n,4),
        "baseline_winner_brier":round(sum((r["baseline_win_prob"]-r["home_win"])**2 for r in predictions)/n,4)}
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--start",type=int,default=2016)
    parser.add_argument("--end",type=int,default=2026)
    parser.add_argument("--iterations",type=int,default=1000)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.iterations<100:raise ValueError("iterations must be >= 100")
    raw=nfl.load_schedules(list(range(args.start,args.end+1))).to_dicts()
    seasons=defaultdict(list)
    for row in raw:
        if str(row.get("game_type","REG")).upper()!="REG":continue
        try:
            season=int(row["season"]);week=int(row["week"])
            hs=float(row["home_score"]);aw=float(row["away_score"])
        except (TypeError,ValueError,KeyError):continue
        if not all(math.isfinite(v) and v>=0 for v in (hs,aw)):continue
        if not row.get("home_team") or not row.get("away_team"):continue
        seasons[season].append((week,row,hs,aw))
    results=[]
    for season, games in sorted(seasons.items()):
        history=defaultdict(list)
        # Strict week boundary: all predictions in a week use history from prior weeks.
        weeks=defaultdict(list)
        for week,row,hs,aw in games:weeks[week].append((row,hs,aw))
        for week in sorted(weeks):
            for row,hs,aw in weeks[week]:
                home=str(row["home_team"]);away=str(row["away_team"])
                if len(history[home])<3 or len(history[away])<3:continue
                # Recent team scoring means, using no current or future scores.
                hm=sum(history[home][-5:])/len(history[home][-5:])
                am=sum(history[away][-5:])/len(history[away][-5:])
                result=simulate({"team":home,"points":hm},{"team":away,"points":am},
                                iterations=args.iterations,seed=season*1000+week*31+sum(map(ord,home+away)))
                # Independent simple normal baseline win probability.
                margin=hm-am
                baseline=.5*(1+math.erf(margin/(math.sqrt(2)*14)))
                results.append({"season":season,"week":week,"home_actual":hs,"away_actual":aw,
                    "home_pred":result["teams"][home]["mean"],"away_pred":result["teams"][away]["mean"],
                    "total_actual":hs+aw,"total_pred":result["teams"][home]["mean"]+result["teams"][away]["mean"],
                    "total_lo":result["total_points"]["p10"],"total_hi":result["total_points"]["p90"],
                    "home_win":1.0 if hs>aw else (0.5 if hs==aw else 0.0),
                    "home_win_prob":result["home_win_probability"]+.5*result["tie_probability"],
                    "baseline_win_prob":baseline})
            for row,hs,aw in weeks[week]:
                history[str(row["home_team"])].append(hs)
                history[str(row["away_team"])].append(aw)
    train=[r for r in results if r["season"]<=args.end-2]
    holdout=[r for r in results if r["season"]>=args.end-1]
    report={"research_only":True,"production_changed":False,
            "limitations":["Only score distributions validated; player correlations and prop probabilities remain uncalibrated",
                           "Team scoring means use last five completed games, not the full live model",
                           "Fixed simulation dispersion is hypothetical, not fitted on training data",
                           "2026 season may be incomplete"],
            "training_seasons":[args.start,args.end-2],
            "holdout_seasons":[args.end-1,args.end],
            "training":score_metrics(train),"holdout":score_metrics(holdout),
            "by_season":{str(s):score_metrics([r for r in results if r["season"]==s]) for s in range(args.start,args.end+1)},
            "approved_for_promotion":False}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"training":report["training"],"holdout":report["holdout"]},indent=2))
if __name__=="__main__":main()
