"""Compare expanded/recent player ML windows on later untouched seasons.

Retrospective evidence only. All algorithms and feature sets are scored on
identical rows, and each holdout trains on earlier seasons only.
"""
import json,math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from scripts.freeze_player_ml_predictions import fit
from tools.ml_card_rotation import load_yard_training,train_yard_form,NAMES,YARDS

OUT=Path('data/ml-card-history-evaluation.json')

def evaluate(rows,target):
    seasons=sorted({int(r['season']) for r in rows if (int(r['season']),int(r['week']))<target})[-2:]
    report=[]
    for season in seasons:
        held=[r for r in rows if int(r['season'])==season and (int(r['season']),int(r['week']))<target and r.get('market') in YARDS]
        predictions=defaultdict(dict)
        for window in ('full','recent'):
            train=[r for r in rows if int(r['season'])<season and (window=='full' or int(r['season'])>=season-2)]
            basic=fit(train,(season,1));form=train_yard_form(train,(season,1))
            for market in sorted(YARDS):
                subset=[r for r in held if r['market']==market]
                if len(subset)<30 or market not in basic or market not in form:continue
                try:
                    xb=np.array([[float(r['new']),float(r['week'])] for r in subset])
                    xf=np.array([[float(r['new']),float(r['old']),float(r['prior_games']),round(float(r['recent_volume']),1),float(r['recent_yards']),float(r['week'])] for r in subset])
                    y=np.array([float(r['actual']) for r in subset]);baseline=float(np.mean(abs(y-xb[:,0])))
                    if not all(np.isfinite(a).all() for a in (xb,xf,y)):continue
                    group=predictions[market];group['samples']=len(subset);group['baseline_mae']=round(baseline,3)
                    metrics=group.setdefault('models',{})
                    for n in NAMES:
                        for feature,model,x in (('basic',basic[market][n],xb),('form',form[market][n],xf)):
                            pred=np.maximum(0,model.predict(x))
                            metrics[f'{n}_{window}_{feature}']=round(float(np.mean(abs(y-pred))),3)
                except (KeyError,TypeError,ValueError,OverflowError):continue
        for market,values in sorted(predictions.items()):
            metrics=values['models'];winner=min(metrics,key=metrics.get)
            report.append({'holdout_season':season,'market':market,**values,
                           'best_model':winner,'best_mae':metrics[winner]})
        print(f'Evaluated held-out {season}: {len(predictions)} player markets',flush=True)
    return {'research_only':True,'production_changed':False,
            'method':'Season holdouts; each model trains on prior seasons only; full and two-season windows use identical held-out rows. Current target week is excluded.',
            'target_season':target[0],'target_week':target[1],'results':report}

def main():
    data=json.loads(Path('data/live-v2.json').read_text());target=(int(data['season']),int(data['week']))
    rows,version,coverage=load_yard_training(target)
    if version!='same-refresh-v2':raise SystemExit('Validated full-history archive unavailable; cannot evaluate expanded windows')
    result=evaluate(rows,target)
    if not result['results']:raise SystemExit('No valid held-out comparisons; retaining existing report')
    result.update(generated_at_utc=datetime.now(timezone.utc).isoformat(),training_coverage=coverage)
    temp=OUT.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2)+'\n');temp.replace(OUT)
    print('Historical comparisons:',len(result['results']))
if __name__=='__main__':main()
