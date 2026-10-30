"""V3 research gate: choose candidates on 2024, evaluate untouched 2025.

This is the first challenger harness, not the final gradient-boosted V3 model.
No production forecast files are read or changed.
"""
import json
from collections import defaultdict
from pathlib import Path
from research.walkforward_2024_2025 import run, MARKETS
import nflreadpy as nfl

CANDIDATES=('baseline','workload','matchup','injury','baseline_workload_blend')
def estimate(row, candidate):
    if candidate=='baseline_workload_blend':
        return .5*row['baseline']+.5*row['workload']
    return row[candidate]

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
        selected=min(CANDIDATES,key=lambda name:score(train,name))
        base=score(test,'baseline')
        challenger=score(test,selected)
        results[market]={
            'selected_on_2024':selected,
            'selection_2024_mae':round(score(train,selected),4),
            'test_2025_n':len(test),
            'baseline_2025_mae':round(base,4),
            'challenger_2025_mae':round(challenger,4),
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
    lines=['# FOURTHDOWN V3 challenger — first holdout gate','','**Live V2 remains unchanged.**','','Candidates selected using 2024 MAE; evaluated on untouched 2025. This is a preliminary model-selection gate, not a final V3 or full production V2 comparison.','','| Market | Selected using 2024 | 2025 N | Baseline MAE | Challenger MAE | Delta | Pass |','|---|---|---:|---:|---:|---:|---|']
    for market,r in results.items():
        lines.append(f"| {market.replace('_',' ')} | {r['selected_on_2024']} | {r['test_2025_n']} | {r['baseline_2025_mae']:.2f} | {r['challenger_2025_mae']:.2f} | {r['change_2025_mae']:+.2f} | {'Yes' if r['passes_holdout'] else 'No'} |")
    lines+=['','## Limitations','','- The candidate family is limited to the existing research formulas; gradient boosting and regression are **not implemented yet**.','- 2024 is used for candidate selection and 2025 is held out; neither is used for a final production decision without additional chronological folds.','- Historical injury data here is a lagged proxy; same-week kickoff-verified injury reconstruction is pending.','- This baseline is not an exact replay of live V2.','- No DraftKings lines or calibrated Over/Under probabilities are evaluated yet.','- Do not promote any model automatically.']
    (dest/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))
if __name__=='__main__':main()
