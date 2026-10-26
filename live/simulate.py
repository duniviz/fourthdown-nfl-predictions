"""Reproducible 10,000-draw exploratory simulations of published NFL forecasts.

Distributions are assumptions pending historical calibration. No betting edges
or calibrated probabilities are claimed.
"""
import json
import math
import random
import hashlib
from datetime import datetime, timezone
from pathlib import Path

DRAWS=10000
def quantile(values,p):
    v=sorted(values)
    return round(v[min(len(v)-1,max(0,int(p*(len(v)-1))))],1)

def simulate_games(games):
    output=[]
    for game in games:
        home=float(game["projected_home_score"])
        away=float(game["projected_away_score"])
        seed=int(hashlib.sha256(str(game["game_id"]).encode()).hexdigest()[:16],16)
        rng=random.Random(seed)
        home_scores=[];away_scores=[];totals=[];margins=[]
        wins=ties=0
        for _ in range(DRAWS):
            # Shared pace/game environment introduces positive scoring correlation.
            pace=rng.gauss(0,3.0)
            h=max(0,round(rng.gauss(home+pace,10.0)))
            a=max(0,round(rng.gauss(away+pace,10.0)))
            home_scores.append(h);away_scores.append(a);totals.append(h+a);margins.append(h-a)
            wins+=h>a
            ties+=h==a
        output.append(dict(game_id=game["game_id"],home=game["home"],away=game["away"],
            simulations=DRAWS,home_win_pct=round(wins/DRAWS*100,1),
            away_win_pct=round((DRAWS-wins-ties)/DRAWS*100,1),
            tie_pct=round(ties/DRAWS*100,1),
            home_score_median=quantile(home_scores,.5),away_score_median=quantile(away_scores,.5),
            total_median=quantile(totals,.5),total_p10=quantile(totals,.1),
            total_p90=quantile(totals,.9),margin_home_p10=quantile(margins,.1),
            margin_home_p90=quantile(margins,.9)))
    return output

def simulate_players(players):
    output=[]
    for player in players:
        mu=max(0,float(player.get("projection") or 0))
        sigma=max(3,float(player.get("uncertainty_yards") or mu*.5))
        seed=int(hashlib.sha256((str(player.get("game_id"))+str(player.get("player_id"))+str(player.get("stat_key"))).encode()).hexdigest()[:16],16)
        rng=random.Random(seed)
        # Nonnegative, right-skewed yardage; parameters matched to mean and SD.
        shape=max(.25,(mu/max(1,sigma))**2)
        scale=mu/shape if mu else 0
        vals=[rng.gammavariate(shape,scale) if mu else 0 for _ in range(DRAWS)]
        entry=dict(game_id=player.get("game_id"),player_id=player.get("player_id"),
            stat_key=player.get("stat_key"),player=player.get("player"),
            simulations=DRAWS,mean_projection=round(mu,1),median=quantile(vals,.5),
            p10=quantile(vals,.1),p90=quantile(vals,.9))
        line=player.get("dk_line")
        if line is not None and line!="" and math.isfinite(float(line)):
            threshold=float(line)
            entry["dk_line"]=threshold
            entry["over_pct"]=round(100*sum(x>threshold for x in vals)/DRAWS,1)
            entry["under_pct"]=round(100*sum(x<threshold for x in vals)/DRAWS,1)
            entry["push_pct"]=round(100*sum(x==threshold for x in vals)/DRAWS,1)
        entry["sorted_draws"]=[round(v,1) for v in sorted(vals)]
        output.append(entry)
    return output

def main():
    games=json.loads(Path("data/live-v2.json").read_text())["games"]
    players=json.loads(Path("data/player-research.json").read_text())["players"]
    result=dict(generated_at_utc=datetime.now(timezone.utc).isoformat(),simulations=DRAWS,
        status="exploratory_uncalibrated",distribution_note="Gaussian correlated team scores and gamma player yardage; historical calibration pending",
        games=simulate_games(games),players=simulate_players(players))
    Path("data/simulations.json").write_text(json.dumps(result,indent=2)+"\n")
    print(f"Simulated {len(result['games'])} games and {len(result['players'])} player markets {DRAWS} times each")
if __name__=="__main__": main()
