"""Research-only correlated matchup Monte Carlo.

Inputs are existing pregame team means and player means. This module does not
estimate those means, infer sportsbook edges, or modify production forecasts.
Common team game-script shocks correlate passing, rushing and receiving outcomes.
"""
import argparse
import json
import math
import random
from pathlib import Path

def _nonnegative(value, name):
    value=float(value)
    if not math.isfinite(value) or value<0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return value

def simulate(home, away, players=(), *, iterations=10000, seed=42):
    """Return reproducible joint samples and marginal summary statistics.

    home/away: {team, points}; players: {id, team, market, mean, line?}.
    Player markets: passing_yards, rushing_yards, receiving_yards.
    All distribution scales and dependencies are *hypotheses* until calibrated
    against frozen historical forecasts; reported probabilities are uncalibrated.
    """
    if not isinstance(iterations,int) or not 100<=iterations<=100000:
        raise ValueError("iterations must be between 100 and 100000")
    teams=(str(home["team"]),str(away["team"]))
    if teams[0]==teams[1]:raise ValueError("Teams must differ")
    points=[_nonnegative(home["points"],"home points"),_nonnegative(away["points"],"away points")]
    valid={"passing_yards","rushing_yards","receiving_yards"}
    roster=[]
    seen=set()
    for p in players:
        if p["team"] not in teams or p["market"] not in valid:
            raise ValueError("Invalid player team or market")
        key=(str(p["id"]),p["market"])
        if key in seen:raise ValueError("Duplicate player market")
        seen.add(key)
        roster.append({**p,"mean":_nonnegative(p["mean"],"player mean"),
                       "line":_nonnegative(p["line"],"line") if p.get("line") is not None else None})
    rng=random.Random(seed)
    results={t:[] for t in teams}
    outcomes={str(i):[] for i in range(len(roster))}
    for _ in range(iterations):
        pace=rng.gauss(0,1)
        # Shared game pace and scoring environment.
        game_env=rng.gauss(0,1)
        scores=[]
        for mu in points:
            scores.append(max(0,mu+3.0*pace+4.0*game_env+rng.gauss(0,8)))
        for t,s in zip(teams,scores):results[t].append(s)
        for i,p in enumerate(roster):
            idx=teams.index(p["team"])
            margin=scores[idx]-scores[1-idx]
            # Trailing scripts increase air volume and reduce rushing volume.
            script=max(-.12,min(.12,-margin*.004 if p["market"]!="rushing_yards" else margin*.006))
            # Common per-team shock is supplied below from the scoring residual.
            # Higher scoring games lift passing and receiving volume together.
            scoring=(scores[idx]-points[idx])/max(12.0,points[idx])
            multiplier=max(.4,1+script+.25*scoring+.06*pace)
            sd=max(4,p["mean"]*(.27 if p["market"]=="passing_yards" else .50))
            value=max(0,p["mean"]*multiplier+rng.gauss(0,sd))
            outcomes[str(i)].append(value)
    def quantile(values,q):
        a=sorted(values);at=q*(len(a)-1);lo=int(at);hi=min(len(a)-1,lo+1)
        return round(a[lo]+(a[hi]-a[lo])*(at-lo),1)
    summary={}
    for t,values in results.items():
        summary[t]={"mean":round(sum(values)/iterations,2),
                    "p10":quantile(values,.1),"p50":quantile(values,.5),"p90":quantile(values,.9)}
    margin=[a-b for a,b in zip(results[teams[0]],results[teams[1]])]
    total=[a+b for a,b in zip(results[teams[0]],results[teams[1]])]
    output={"research_only":True,"calibrated":False,"iterations":iterations,"seed":seed,
            "teams":summary,"home_win_probability":round(sum(x>0 for x in margin)/iterations,4),
            "tie_probability":round(sum(x==0 for x in margin)/iterations,4),
            "total_points":{"p10":quantile(total,.1),"p50":quantile(total,.5),"p90":quantile(total,.9)},
            "players":[]}
    for i,p in enumerate(roster):
        values=outcomes[str(i)]
        entry={"id":p["id"],"team":p["team"],"market":p["market"],"input_mean":p["mean"],
               "simulated_mean":round(sum(values)/iterations,2),
               "p10":quantile(values,.1),"p50":quantile(values,.5),"p90":quantile(values,.9)}
        if p["line"] is not None:
            entry["line"]=p["line"]
            entry["over_probability_uncalibrated"]=round(sum(v>p["line"] for v in values)/iterations,4)
        output["players"].append(entry)
    return output

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,required=True,help="JSON with home, away and players")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--iterations",type=int,default=10000)
    parser.add_argument("--seed",type=int,default=42)
    args=parser.parse_args()
    payload=json.loads(args.input.read_text())
    result=simulate(payload["home"],payload["away"],payload.get("players",[]),iterations=args.iterations,seed=args.seed)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(f"Research simulation completed: {result['iterations']} joint draws; uncalibrated.")
if __name__=="__main__":main()
