"""Train simple portable player ML models and make paired-evidence decisions.

This uses the historical walk-forward backtest CSV for fitting. Promotion uses
only actual frozen pregame pair records graded by live.player_results.
"""
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from live.player_ml_runtime import MARKETS, MODEL_FAMILY

MIN_TRAIN=100
MIN_PAIRED=100
MIN_WEEKS=4
MIN_RECENT=20
PROMOTION_GAIN=.03
ROLLBACK_LOSS=.10


def train(rows):
    groups=defaultdict(list)
    for r in rows:
        try:
            market=r['market']; season=int(r['season']); week=int(r['week'])
            base=float(r['new']); actual=float(r['actual'])
            if market not in MARKETS or not all(math.isfinite(v) and v>=0 for v in (base,actual)): continue
            groups[market].append((season,week,base,actual))
        except (KeyError,ValueError,TypeError):continue
    result={}
    for market, items in groups.items():
        if len(items)<MIN_TRAIN: continue
        model=make_pipeline(StandardScaler(),Ridge(alpha=100.0))
        model.fit(np.asarray([[x[2],x[1]] for x in items]),np.asarray([x[3] for x in items]))
        scaler=model.named_steps['standardscaler']; ridge=model.named_steps['ridge']
        coeff=ridge.coef_/scaler.scale_
        intercept=float(ridge.intercept_-np.dot(coeff,scaler.mean_))
        cutoff=max((x[0],x[1]) for x in items)
        result[market]={'coefficients':[float(x) for x in coeff], 'intercept':intercept,
                        'trained_season':cutoff[0], 'trained_week':cutoff[1], 'training_rows':len(items)}
    return result


def decide(rows, previous):
    grouped=defaultdict(list)
    # Duplicate records must not count as independent evidence.
    counts=defaultdict(int)
    for r in rows:
        counts[(r.get('game_id'),r.get('player_id'),r.get('stat_key'))] += 1
    for r in rows:
        identity=(r.get('game_id'),r.get('player_id'),r.get('stat_key'))
        if not all(identity) or counts[identity] != 1: continue
        pair=r.get('player_ml_pair'); parts=str(r.get('game_id') or '').split('_')
        if not isinstance(pair,dict) or pair.get('family') != MODEL_FAMILY or len(parts)<2:continue
        try:
            wk=(int(parts[0]),int(parts[1])); market=r['stat_key']
            if (int(pair['trained_season']),int(pair['trained_week'])) >= wk:continue
            base=float(pair['baseline']); candidate=float(pair['candidate']); actual=float(r['actual'])
            if market not in MARKETS or not all(math.isfinite(x) and x>=0 for x in (base,candidate,actual)):continue
            grouped[market].append((wk,abs(base-actual),abs(candidate-actual)))
        except (KeyError,TypeError,ValueError):continue
    decisions={}
    for market in MARKETS:
        observations=grouped.get(market,[])
        weeks=sorted({r[0] for r in observations})
        rolling=[r for r in observations if r[0] in weeks[-8:]]
        recent=[r for r in observations if r[0] in weeks[-2:]]
        previous_active=previous.get(market,{}).get('active') is True
        def mae(rs,i): return sum(x[i] for x in rs)/len(rs) if rs else None
        b,c=mae(rolling,1),mae(rolling,2); rb,rc=mae(recent,1),mae(recent,2)
        recent_bad=len(recent)>=MIN_RECENT and rb is not None and rc > rb*(1+ROLLBACK_LOSS)
        eligible=(len(rolling)>=MIN_PAIRED and len(weeks[-8:])>=MIN_WEEKS and b is not None and b>0
                  and c<=b*(1-PROMOTION_GAIN) and len(recent)>=MIN_RECENT and not recent_bad)
        # No new promotion when data are sparse; a previously active model is
        # disabled if rolling evidence no longer supports it or recent results worsen.
        active=bool(eligible and not recent_bad)
        reason=('promoted' if active and not previous_active else 'retained' if active else
                'rolled_back' if previous_active else 'awaiting_paired_evidence')
        decisions[market]={'active':active,'reason':reason,'paired':len(rolling),'weeks':len(weeks[-8:]),
            'baseline_mae':round(b,3) if b is not None else None,'candidate_mae':round(c,3) if c is not None else None,
            'recent_paired':len(recent),'recent_baseline_mae':round(rb,3) if rb is not None else None,
            'recent_candidate_mae':round(rc,3) if rc is not None else None}
    return decisions


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);a=p.parse_args()
    with a.input.open(newline='',encoding='utf-8-sig') as f: models=train(list(csv.DictReader(f)))
    if not models: raise SystemExit('No deployable models trained; previous runtime retained')
    path=Path('data/player-ml-runtime.json')
    try: previous=json.loads(path.read_text())
    except (OSError,ValueError):previous={}
    results=json.loads(Path('data/player-results.json').read_text()).get('rows',[])
    decisions=decide(results,previous.get('decisions',{}) if previous.get('family')==MODEL_FAMILY else {})
    # Missing model cannot be active.
    for market in MARKETS:
        if market not in models:decisions[market].update(active=False,reason='missing_trained_model')
    runtime={'family':MODEL_FAMILY,'generated_at_utc':datetime.now(timezone.utc).isoformat(),
             'policy':'100 paired forecasts over at least 4 of last 8 weeks; 3% improvement; 20 recent forecasts; rollback if recent MAE worsens by 10%',
             'models':models,'decisions':decisions}
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(runtime,indent=2)+'\n');tmp.replace(path)
    print(json.dumps(decisions,indent=2))
if __name__=='__main__': main()
