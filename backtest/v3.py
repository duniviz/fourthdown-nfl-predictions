"""FOURTHDOWN v3: Elo plus v2 and train-only probability calibration.

All features are produced chronologically. The 2025 season is reserved for
evaluation; calibration parameters are fitted using 2021-2024 only.
QB/injury features are NOT included without timestamped historical data.
"""
import json
import math
from pathlib import Path
from collections import defaultdict
from .rolling import load_rows
from .v2 import build_v2_predictions

def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-max(-35.0, min(35.0, x))))

def elo_predictions(schedules, k=20.0, home_elo=55.0, carryover=0.75):
    ratings={}
    previous_season=None
    result={}
    grouped=defaultdict(list)
    for g in schedules:
        if g.get("game_type","REG")!="REG": continue
        if not g.get("home_score") or not g.get("away_score"): continue
        grouped[(int(g["season"]),int(g["week"]))].append(g)
    for season,week in sorted(grouped):
        if previous_season != season:
            ratings={t:1500+(v-1500)*carryover for t,v in ratings.items()}
            previous_season=season
        pending=[]
        for g in grouped[(season,week)]:
            home,away=g["home_team"],g["away_team"]
            rh,ra=ratings.get(home,1500),ratings.get(away,1500)
            diff=rh+home_elo-ra
            p=sigmoid(math.log(10)*diff/400)
            result[g["game_id"]]={"elo_margin":diff/25.0,"elo_home_probability":p}
            actual_h,actual_a=float(g["home_score"]),float(g["away_score"])
            outcome=1 if actual_h>actual_a else 0 if actual_h<actual_a else .5
            delta=k*(outcome-p)
            pending.append((home,away,delta))
        # Apply ratings after the whole week, preventing within-week leakage.
        for home,away,delta in pending:
            ratings[home]=ratings.get(home,1500)+delta
            ratings[away]=ratings.get(away,1500)-delta
    return result

def fit_logistic(xs, ys, iterations=3500, lr=.025, reg=.02):
    """Train-only standardized logistic regression with regularization."""
    n=len(xs)
    means=[sum(x[j] for x in xs)/n for j in range(2)]
    scales=[max(.01,(sum((x[j]-means[j])**2 for x in xs)/n)**.5) for j in range(2)]
    normalized=[[(x[j]-means[j])/scales[j] for j in range(2)] for x in xs]
    weights=[0.0,0.0,0.0]
    for _ in range(iterations):
        grad=[0.0,0.0,0.0]
        for x,y in zip(normalized,ys):
            error=sigmoid(weights[0]+weights[1]*x[0]+weights[2]*x[1])-y
            grad[0]+=error
            grad[1]+=error*x[0]
            grad[2]+=error*x[1]
        for j in range(3):
            weights[j]-=lr*(grad[j]/n+(reg*weights[j] if j else 0))
    return {"means":means,"scales":scales,"weights":weights}

def predict(model,x):
    z=model["weights"][0]+sum(model["weights"][j+1]*(x[j]-model["means"][j])/model["scales"][j] for j in range(2))
    return sigmoid(z)

def scores(rows,prob_fn):
    if not rows: return {"games":0}
    probs=[prob_fn(r) for r in rows]
    ys=[int(r["actual_margin"]>0) for r in rows]
    n=len(rows)
    return {
        "games":n,
        "winner_accuracy":round(sum((p>=.5)==bool(y) for p,y in zip(probs,ys))/n,4),
        "brier":round(sum((p-y)**2 for p,y in zip(probs,ys))/n,5),
        "log_loss":round(-sum(y*math.log(max(1e-10,p))+(1-y)*math.log(max(1e-10,1-p)) for p,y in zip(probs,ys))/n,5),
    }

def run(schedules,team_games):
    v2=build_v2_predictions(schedules,team_games)
    elo=elo_predictions(schedules)
    rows=[]
    for g in v2:
        if g["game_id"] not in elo or g["actual_margin"]==0: continue
        rows.append({**g,**elo[g["game_id"]]})
    train=[r for r in rows if 2021<=r["season"]<=2024]
    test=[r for r in rows if r["season"]==2025]
    if not train or not test: raise ValueError("Training or held-out 2025 games missing")
    xs=[[r["pred_margin"],r["elo_margin"]] for r in train]
    ys=[int(r["actual_margin"]>0) for r in train]
    fitted=fit_logistic(xs,ys)
    v2_prob=lambda r:sigmoid(r["pred_margin"]/10.0)
    elo_prob=lambda r:r["elo_home_probability"]
    v3_prob=lambda r:predict(fitted,[r["pred_margin"],r["elo_margin"]])
    def report(part):
        return {"v2_uncalibrated":scores(part,v2_prob),
                "elo":scores(part,elo_prob),
                "v3_elo_plus_v2_calibrated":scores(part,v3_prob)}
    return {
        "training_2021_2024":report(train),
        "held_out_2025":report(test),
        "calibration_training_games":len(train),
        "held_out_games":len(test),
        "qb_adjustment":"NOT TESTED - no timestamped historical starter/injury features",
        "injury_adjustment":"NOT TESTED - no timestamped historical injury data",
        "caveats":[
            "2025 is held out from coefficient fitting; prior development decisions may have inspected 2025, so this is not a pristine never-seen final test.",
            "Elo parameters are preset, not independently tuned.",
            "Logistic calibration uses training seasons only; training metrics are in-sample.",
            "Market odds and ROI are not evaluated here; winner accuracy is not ATS accuracy.",
            "No claim of improved prediction quality until held-out metrics are examined."
        ],
        "fitted_coefficients":fitted,
    }

def main():
    folder=Path("data")
    print(json.dumps(run(load_rows(folder/"schedules.csv"),load_rows(folder/"team_epa.csv")),indent=2))

if __name__=="__main__":main()
