"""Conservative weekly walk-forward selection of player residual correction weights.

Uses only archived first-published pregame forecasts graded against completed games.
Never optimizes against current/future games or sportsbook lines.
"""
import json
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

CANDIDATES=(0.0,0.25,0.5,0.75,1.0)
MIN_TRAIN=60
MIN_TEST=40
MIN_WEEKS=4
MIN_GAIN=0.15
MAX_BIAS=5.0
MARKETS=("passing_yards","rushing_yards","receiving_yards")

def clamp(v): return max(-MAX_BIAS,min(MAX_BIAS,v))

def evaluate(rows):
    """Return only candidates that beat zero correction on out-of-sample weeks."""
    grouped=defaultdict(lambda:defaultdict(list))
    for row in rows:
        market=row.get("stat_key")
        game=str(row.get("game_id") or "")
        if market not in MARKETS or len(game.split("_"))<2:continue
        try:
            week=int(game.split("_")[1])
            season=int(game.split("_")[0])
            error=float(row["actual"])-float(row["projection"])
        except (TypeError,ValueError,KeyError):continue
        if not -1000<error<1000:continue
        grouped[market][(season,week)].append(error)
    decisions={}
    for market,weeks in grouped.items():
        ordered=sorted(weeks)
        training=[]
        scored={w:[] for w in CANDIDATES}
        test_weeks=0
        for wk in ordered:
            errors=weeks[wk]
            if len(training)>=MIN_TRAIN:
                bias=clamp(sum(training)/len(training))
                for w in CANDIDATES:
                    scored[w].extend(abs(e-w*bias) for e in errors)
                test_weeks+=1
            training.extend(errors)
        baseline=scored[0.0]
        if len(baseline)<MIN_TEST or test_weeks<MIN_WEEKS:
            decisions[market]={"weight":0.0,"status":"insufficient_holdout","samples":len(baseline),"weeks":test_weeks}
            continue
        maes={w:sum(v)/len(v) for w,v in scored.items()}
        winner=min(CANDIDATES,key=lambda w:(maes[w],w))
        improvement=maes[0.0]-maes[winner]
        weight=winner if improvement>=MIN_GAIN else 0.0
        decisions[market]={"weight":weight,"status":"validated" if weight else "baseline_retained",
                           "samples":len(baseline),"weeks":test_weeks,
                           "baseline_mae":round(maes[0.0],3),"candidate_mae":round(maes[winner],3),
                           "improvement_mae":round(improvement,3)}
    for market in MARKETS:
        decisions.setdefault(market,{"weight":0.0,"status":"insufficient_holdout","samples":0,"weeks":0})
    return decisions

def main():
    path=Path("data/player-results.json")
    rows=json.loads(path.read_text(encoding="utf-8")).get("rows",[])
    decisions=evaluate(rows)
    out={"updated_at_utc":datetime.now(timezone.utc).isoformat(),
         "method":"Week-blocked walk-forward residual correction; zero-weight baseline, minimum 60 prior forecasts, 40 holdout forecasts across 4 weeks, >0.15 yards MAE improvement",
         "weights":decisions}
    Path("data/player-weight-learning.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print("Weekly player weight audit:",decisions)

if __name__=="__main__":main()
