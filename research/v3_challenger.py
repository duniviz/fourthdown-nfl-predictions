"""V3 research gate: choose candidates on 2024, evaluate untouched 2025.

This is the first challenger harness, not the final gradient-boosted V3 model.
No production forecast files are read or changed.
"""
import json
from collections import defaultdict
from pathlib import Path
from research.walkforward_2024_2025 import run, MARKETS
import nflreadpy as nfl

from itertools import product
from math import sqrt
BASE_FEATURES=('baseline','workload','matchup','injury')
# Exhaustive nonnegative weights in 25% increments, summing to 100%.
# Includes individual metrics and all two-, three-, four-way blends.
WEIGHT_GRID={('mix_'+''.join(str(w) for w in weights)):weights
             for weights in product(range(5),repeat=4) if sum(weights)==4}

CANDIDATES=('baseline','workload','matchup','injury','baseline_workload_blend',
            'workload_matchup_blend','workload_injury_blend','matchup_injury_blend',
            'three_way_blend','four_way_blend')
def estimate(row, candidate):
    if candidate=='baseline_workload_blend':
        return .5*row['baseline']+.5*row['workload']
    blends={
        'workload_matchup_blend':('workload','matchup'),
        'workload_injury_blend':('workload','injury'),
        'matchup_injury_blend':('matchup','injury'),
        'three_way_blend':('workload','matchup','injury'),
        'four_way_blend':('baseline','workload','matchup','injury'),
    }
    if candidate in blends:
        keys=blends[candidate]
        return sum(row[k] for k in keys)/len(keys)
    if candidate in WEIGHT_GRID:\n        return sum(row[k]*w/4 for k,w in zip(BASE_FEATURES,WEIGHT_GRID[candidate]))\n    return row[candidate]

ALL_CANDIDATES=tuple(dict.fromkeys((*CANDIDATES,*WEIGHT_GRID)))
def rmse(rows,candidate):
    return sqrt(sum((estimate(r,candidate)-r['actual'])**2 for r in rows)/len(rows)) if rows else None

def weekly_consistency(rows,candidate):
    weeks=defaultdict(list)
    for row in rows:weeks[(row['season'],row['week'])].append(row)
    return [{'season':s,'week':w,'n':len(batch),'mae':round(score(batch,candidate),4)}
            for (s,w),batch in sorted(weeks.items())]

def score(rows, candidate):
    if not rows: return None
    return sum(abs(estimate(r,candidate)-r['actual']) for r in rows)/len(rows)

def evaluate(records):
    grouped=defaultdict(list)
    for r in records:
        if r['market'] in MARKETS and r['season'] in (2024,2025):
            grouped[(r['season'],r['market'])].append(r)
    results={}
    for market in MARKETS:
        train=grouped[(2024,market)]
        test=grouped[(2025,market)]
        if not train or not test: continue
        # Choose once using 2024 only. No peeking at 2025 results.
        selected=min(ALL_CANDIDATES,key=lambda name:(score(train,name),rmse(train,name)))
        base=score(test,'baseline')
        challenger=score(test,selected)
        ranking=sorted(({'model':name,'mae':round(score(test,name),4)} for name in ALL_CANDIDATES),
                       key=lambda item:item['mae'])
        results[market]={
            'same_slate_2025_all_candidates':ranking,
            'candidate_count':len(ALL_CANDIDATES),
            'selected_on_2024':selected,
            'selection_2024_mae':round(score(train,selected),4),
            'test_2025_n':len(test),
            'baseline_2025_mae':round(base,4),
            'challenger_2025_mae':round(challenger,4),\n            'baseline_2025_rmse':round(rmse(test,'baseline'),4),\n            'challenger_2025_rmse':round(rmse(test,selected),4),\n            'weekly_consistency_2025':weekly_consistency(test,selected),\n            'selected_weights':dict(zip(BASE_FEATURES,[w/4 for w in WEIGHT_GRID[selected]])) if selected in WEIGHT_GRID else None,
            'change_2025_mae':round(challenger-base,4),
            'passes_holdout':challenger<base,
        }
    return results

def main():
    records=run(nfl.load_player_stats([2024,2025]).to_dicts(),
                nfl.load_snap_counts([2024,2025]).to_dicts(),
                nfl.load_injuries([2024,2025]).to_dicts())
    results=evaluate(records)
    if len(results)!=len(MARKETS): raise RuntimeError('Incomplete holdout coverage')
    dest=Path('research/v3-results');dest.mkdir(parents=True,exist_ok=True)
    (dest/'results.json').write_text(json.dumps({'status':'research_only','trained_on':2024,'holdout':2025,'markets':results},indent=2)+'\n')
    lines=['# FOURTHDOWN V3 challenger — automated metric mix search','','**Live V2 remains unchanged.**','','Candidates selected using 2024 MAE; evaluated on untouched 2025. This is a preliminary model-selection gate, not a final V3 or full production V2 comparison.','','| Market | Selected using 2024 | 2025 N | Baseline MAE | Challenger MAE | Delta | Pass |','|---|---|---:|---:|---:|---:|---|']
    for market,r in results.items():
        lines.append(f"| {market.replace('_',' ')} | {r['selected_on_2024']} | {r['test_2025_n']} | {r['baseline_2025_mae']:.2f} | {r['challenger_2025_mae']:.2f} | {r['change_2025_mae']:+.2f} | {'Yes' if r['passes_holdout'] else 'No'} |")
    lines+=['','## Same-slate 2025 model combination leaderboard','','All candidates forecast the identical eligible player/game/market records. Model selection uses 2024 only; the 2025 ranking is diagnostic, not a retroactive selection.','','| Market | 2025 rank | Candidate | MAE |','|---|---:|---|---:|']
    for market,r in results.items():
        for rank,entry in enumerate(r['same_slate_2025_all_candidates'][:10],1):
            lines.append(f"| {market.replace('_',' ')} | {rank} | {entry['model']} | {entry['mae']:.2f} |")
    lines+=['','## Limitations','','- This searches 25%-increment nonnegative blends of the four existing historical features; it does not discover new raw statistics or implement gradient boosting.','- 2024 is used for candidate selection and 2025 is held out; neither is used for a final production decision without additional chronological folds.','- Historical injury data here is a lagged proxy; same-week kickoff-verified injury reconstruction is pending.','- This baseline is not an exact replay of live V2.','- No DraftKings lines or calibrated Over/Under probabilities are evaluated yet.','- Do not promote any model automatically.']
    (dest/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))
if __name__=='__main__':main()
