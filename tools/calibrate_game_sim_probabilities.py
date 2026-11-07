"""Research-only chronological calibration of simulation win probabilities.

Fits one shrinkage parameter on 2016-2024 and evaluates 2025-2026 once.
No current-season outcomes enter forecasts; no production changes.
"""
import argparse,json,math
from collections import defaultdict
from pathlib import Path
import nflreadpy as nfl
from tools.correlated_game_sim import simulate

SHRINKS=(0.0,.25,.5,.75,1.0)
def brier(rows,key):
    return sum((r[key]-r["outcome"])**2 for r in rows)/len(rows)
def evaluate(rows):
    if not rows:return {"games":0}
    return {"games":len(rows),
        "brier":round(brier(rows,"calibrated"),5),
        "raw_simulation_brier":round(brier(rows,"raw"),5),
        "simple_baseline_brier":round(brier(rows,"baseline"),5),
        "mean_predicted_home_win":round(sum(r["calibrated"] for r in rows)/len(rows),4),
        "observed_home_win":round(sum(r["outcome"] for r in rows)/len(rows),4)}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",type=int,default=2016)
    p.add_argument("--end",type=int,default=2026)
    p.add_argument("--iterations",type=int,default=1000)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    games=defaultdict(lambda:defaultdict(list))
    for g in nfl.load_schedules(list(range(a.start,a.end+1))).to_dicts():
        if str(g.get("game_type","")).upper()!="REG":continue
        try:season=int(g["season"]);week=int(g["week"]);hs=float(g["home_score"]);aw=float(g["away_score"])
        except (KeyError,TypeError,ValueError):continue
        if not all(math.isfinite(x) and x>=0 for x in (hs,aw)):continue
        if not g.get("home_team") or not g.get("away_team"):continue
        games[season][week].append((str(g["home_team"]),str(g["away_team"]),hs,aw))
    rows=[]
    for season,weeks in sorted(games.items()):
        history=defaultdict(list)
        for week,fixtures in sorted(weeks.items()):
            for home,away,hs,aw in fixtures:
                if min(len(history[home]),len(history[away]))<3:continue
                hm=sum(history[home][-5:])/len(history[home][-5:])
                am=sum(history[away][-5:])/len(history[away][-5:])
                sim=simulate({"team":home,"points":hm},{"team":away,"points":am},
                             iterations=a.iterations,seed=season*1000+week*31+sum(map(ord,home+away)))
                raw=sim["home_win_probability"]+.5*sim["tie_probability"]
                baseline=.5*(1+math.erf((hm-am)/(math.sqrt(2)*14)))
                rows.append({"season":season,"raw":raw,"baseline":baseline,
                             "outcome":1.0 if hs>aw else (.5 if hs==aw else 0.0)})
            for home,away,hs,aw in fixtures:
                history[home].append(hs);history[away].append(aw)
    train=[r for r in rows if r["season"]<=a.end-2]
    holdout=[r for r in rows if r["season"]>=a.end-1]
    if not train or not holdout:raise ValueError("Need nonempty training and holdout")
    def calibrate(items,weight):
        return [{**r,"calibrated":weight*r["raw"]+(1-weight)*r["baseline"]} for r in items]
    scores={str(w):round(brier(calibrate(train,w),"calibrated"),6) for w in SHRINKS}
    selected=min(SHRINKS,key=lambda w:(scores[str(w)],w))
    train_eval=evaluate(calibrate(train,selected))
    holdout_eval=evaluate(calibrate(holdout,selected))
    report={"research_only":True,"production_changed":False,
            "method":"Pre-registered shrinkage grid; select only on training Brier, evaluate untouched 2025-2026 holdout",
            "training_seasons":[a.start,a.end-2],"holdout_seasons":[a.end-1,a.end],
            "candidate_simulation_weights":list(SHRINKS),
            "training_grid_brier":scores,"selected_simulation_weight":selected,
            "training":train_eval,"holdout":holdout_eval,
            "holdout_by_season":{str(s):evaluate(calibrate([r for r in holdout if r["season"]==s],selected)) for s in range(a.end-1,a.end+1)},
            "approved_for_promotion":False,
            "limitations":["Compared to a simple scoring baseline, not exact live production probabilities",
                           "No player-prop correlation calibration",
                           "2026 season may be incomplete",
                           "No independent forward shadow evaluation or rollback artifact"]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"selected_simulation_weight":selected,"training":train_eval,"holdout":holdout_eval},indent=2))
if __name__=="__main__":main()
