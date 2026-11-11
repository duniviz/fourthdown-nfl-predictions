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
HISTORICAL_MIN_PAIRED=300
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


def historical_walk_forward(rows):
    """Evaluate the deployable model with chronological, held-out weekly forecasts.

    Each target week is scored using a model fitted only to earlier weeks. The
    research backtest rows are retrospective, so this remains an offline
    qualification signal, distinct from frozen production forecasts.
    """
    by_market=defaultdict(list)
    identity_counts=defaultdict(int)
    for r in rows:
        try:
            season=int(r['season']); week=int(r['week'])
            market=str(r['market']); player=str(r.get('player_id') or '')
            if market not in MARKETS or not player: continue
            identity_counts[(season,week,player,market)]+=1
        except (KeyError,TypeError,ValueError): continue
    for r in rows:
        try:
            season=int(r['season']); week=int(r['week'])
            market=str(r['market']); player=str(r.get('player_id') or '')
            identity=(season,week,player,market)
            base=float(r['new']); actual=float(r['actual'])
            if (market not in MARKETS or not player or identity_counts[identity]!=1
                    or not all(math.isfinite(v) and v>=0 for v in (base,actual))): continue
            by_market[market].append(((season,week),player,base,actual))
        except (KeyError,TypeError,ValueError): continue

    results={}
    for market in MARKETS:
        items=sorted(by_market.get(market,[]),key=lambda x:(x[0],x[1]))
        target_weeks=sorted({row[0] for row in items})
        scored=[]
        for target_week in target_weeks:
            earlier=[row for row in items if row[0]<target_week]
            current=[row for row in items if row[0]==target_week]
            if len(earlier)<MIN_TRAIN: continue
            fit_rows=[{'market':market,'season':wk[0],'week':wk[1],
                       'new':base,'actual':actual} for wk,_,base,actual in earlier]
            fitted=train(fit_rows).get(market)
            if not fitted: continue
            c0,c1=fitted['coefficients']; intercept=fitted['intercept']
            for _,player,base,actual in current:
                prediction=max(0.0,intercept+c0*base+c1*target_week[1])
                prediction=min(base*1.25,max(base*.75,prediction))
                scored.append((target_week,abs(base-actual),abs(prediction-actual)))

        weeks=sorted({row[0] for row in scored})
        rolling=[row for row in scored if row[0] in weeks[-8:]]
        recent=[row for row in scored if row[0] in weeks[-2:]]
        def mae(values,index):
            return sum(row[index] for row in values)/len(values) if values else None
        baseline=mae(rolling,1); candidate=mae(rolling,2)
        recent_baseline=mae(recent,1); recent_candidate=mae(recent,2)
        improvement=((baseline-candidate)/baseline*100) if baseline and candidate is not None else None
        recent_change=((recent_candidate-recent_baseline)/recent_baseline*100) if recent_baseline and recent_candidate is not None else None
        reasons=[]
        if len(rolling)<HISTORICAL_MIN_PAIRED:
            reasons.append(f'Need {HISTORICAL_MIN_PAIRED} held-out forecasts; have {len(rolling)}')
        if len(weeks[-8:])<MIN_WEEKS:
            reasons.append(f'Need results across {MIN_WEEKS} weeks; have {len(weeks[-8:])}')
        if baseline is None or baseline<=0:
            reasons.append('No usable baseline error to compare')
        elif improvement is None or improvement<PROMOTION_GAIN*100:
            reasons.append(f'Need at least {PROMOTION_GAIN*100:.0f}% lower average error; current improvement is {improvement:.1f}%' if improvement is not None else 'Candidate error could not be compared')
        if len(recent)<MIN_RECENT:
            reasons.append(f'Need {MIN_RECENT} recent forecasts; have {len(recent)}')
        elif recent_change is not None and recent_change>ROLLBACK_LOSS*100:
            reasons.append(f'Recent average error worsened by {recent_change:.1f}%')
        eligible=not reasons
        results[market]={'eligible':bool(eligible),'paired':len(rolling),'weeks':len(weeks[-8:]),
            'baseline_mae':round(baseline,3) if baseline is not None else None,
            'candidate_mae':round(candidate,3) if candidate is not None else None,
            'improvement_pct':round(improvement,2) if improvement is not None else None,
            'recent_paired':len(recent),
            'recent_baseline_mae':round(recent_baseline,3) if recent_baseline is not None else None,
            'recent_candidate_mae':round(recent_candidate,3) if recent_candidate is not None else None,
            'recent_change_pct':round(recent_change,2) if recent_change is not None else None,
            'qualification_reasons':reasons}
    return results


def decide(rows, previous, historical=None):
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
            'recent_candidate_mae':round(rc,3) if rc is not None else None,'recent_regression':bool(recent_bad)}
    # Prefer frozen pregame evidence once it has enough weeks. Until then,
    # a qualifying chronological historical replay can seed the initial rollout.
    historical=historical or {}
    for market in MARKETS:
        live=decisions[market]
        replay=historical.get(market,{})
        live_is_decisive=live['paired']>=MIN_PAIRED and live['weeks']>=MIN_WEEKS
        live['historical_walk_forward']=replay
        if not live_is_decisive and not live.get('recent_regression') and replay.get('eligible') is True:
            live.update(active=True,reason='historical_walk_forward_qualified',
                        evidence_source='historical_walk_forward')
        elif not live_is_decisive and replay.get('paired',0)>0:
            live['evidence_source']='historical_walk_forward'
            if not live.get('recent_regression') and live['reason']!='rolled_back':
                live['reason']='historical_not_qualified'
        else:
            live['evidence_source']='frozen_live_pairs'
    return decisions


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);a=p.parse_args()
    with a.input.open(newline='',encoding='utf-8-sig') as f: source_rows=list(csv.DictReader(f))
    models=train(source_rows)
    if not models: raise SystemExit('No deployable models trained; previous runtime retained')
    path=Path('data/player-ml-runtime.json')
    try: previous=json.loads(path.read_text())
    except (OSError,ValueError):previous={}
    results=json.loads(Path('data/player-results.json').read_text()).get('rows',[])
    historical=historical_walk_forward(source_rows)
    decisions=decide(results,previous.get('decisions',{}) if previous.get('family')==MODEL_FAMILY else {},historical)
    # Missing model cannot be active.
    for market in MARKETS:
        if market not in models:decisions[market].update(active=False,reason='missing_trained_model')
    runtime={'family':MODEL_FAMILY,'generated_at_utc':datetime.now(timezone.utc).isoformat(),
             'policy':'Historical walk-forward: 300 held-out forecasts across 4 of the latest 8 weeks, at least 3% MAE gain and 20 recent forecasts; frozen live pairs take precedence after 100 pairs across 4 weeks; rollback if recent MAE worsens by 10%',
             'models':models,'decisions':decisions}
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(runtime,indent=2)+'\n');tmp.replace(path)
    print(json.dumps(decisions,indent=2))
if __name__=='__main__': main()
