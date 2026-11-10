"""Train game ML artifacts and use matched pregame results to deploy or roll back."""
import json, math
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
import nflreadpy as nfl
from scripts.freeze_game_ml_predictions import train
from live.game_ml_runtime import FAMILY,MARKETS
from live.game_pregame_observations import dt,number


def pairs(observations,results):
    completed={str(r.get('game_id')):r for r in results}; best={}
    for row in observations:
        shadow=row.get('game_ml_shadow')
        if not isinstance(shadow,dict) or shadow.get('family')!=FAMILY:continue
        gid=str(row.get('game_id') or ''); result=completed.get(gid)
        kick=dt(row.get('kickoff_utc'));captured=dt(row.get('captured_at_utc'));forecast=dt(row.get('forecast_at_utc'));quote=dt(row.get('dk_at_utc'))
        if not result or not kick or not captured or not forecast or not quote:continue
        if (row.get('home'),row.get('away')) != (result.get('home'),result.get('away')):continue
        cutoff=kick-timedelta(minutes=15)
        if not (forecast<=captured<=cutoff and quote<=captured):continue
        if gid not in best or (captured,forecast)>best[gid][0]:best[gid]=((captured,forecast),row,result)
    out=[]
    for _,row,res in best.values():
        home=number(res.get('home_score'));away=number(res.get('away_score'))
        if home is None or away is None:continue
        for market,pair in row['game_ml_shadow'].get('markets',{}).items():
            if market not in MARKETS or not isinstance(pair,dict):continue
            base=number(pair.get('baseline'));candidate=number(pair.get('candidate'))
            try:
                game_week=(int(row['season']),int(row['week']))
                trained=(int(pair['trained_season']),int(pair['trained_week']))
            except (KeyError,TypeError,ValueError):continue
            if None in (base,candidate) or trained>=game_week:continue
            actual=home-away if market=='game_margin_home' else home+away
            spread_time=dt(row.get('dk_home_spread_observed_at_utc') or row.get('dk_at_utc'))
            total_time=dt(row.get('dk_total_observed_at_utc') or row.get('dk_at_utc'))
            spread=number(row.get('dk_home_spread')) if spread_time and spread_time<=captured else None
            line=number(row.get('dk_total')) if total_time and total_time<=captured else None
            out.append({'game_id':row['game_id'],'week':game_week,'market':market,'baseline':base,'candidate':candidate,'actual':actual,
                        'spread':spread,'line':line})
    return out


def decide(records,previous):
    out={}
    def score(x): return 1 if x>0 else -1 if x<0 else 0
    for market in MARKETS:
        rows=[r for r in records if r['market']==market]
        weeks=sorted({r['week'] for r in rows});window=[r for r in rows if r['week'] in weeks[-12:]]
        recent=[r for r in rows if r['week'] in weeks[-2:]]
        def mae(rs,field):return sum(abs(r[field]-r['actual']) for r in rs)/len(rs) if rs else None
        b=mae(window,'baseline');c=mae(window,'candidate');rb=mae(recent,'baseline');rc=mae(recent,'candidate')
        def hitrates(kind):
            comparable=[]
            for r in window:
                shift=0 if kind=='winner' else r['spread'] if kind=='ats' else -r['line'] if r['line'] is not None else None
                if shift is None:continue
                actual=score(r['actual']+shift);base=score(r['baseline']+shift);cand=score(r['candidate']+shift)
                if 0 in (actual,base,cand):continue
                comparable.append((base==actual,cand==actual))
            return len(comparable),sum(a for a,_ in comparable),sum(b for _,b in comparable)
        categories=('winner','ats') if market=='game_margin_home' else ('ou',)
        checks={k:hitrates(k) for k in categories}
        pick_ok=all(n>=40 and cand>=base for n,base,cand in checks.values())
        recent_bad=len(recent)>=20 and rb is not None and rc>rb*1.10
        eligible=(len(window)>=100 and len(weeks[-12:])>=6 and b is not None and b>0 and c<=b*.97
                  and len(recent)>=20 and pick_ok and not recent_bad)
        was_active=previous.get(market,{}).get('active') is True
        out[market]={'active':bool(eligible),'reason':'promoted' if eligible and not was_active else 'retained' if eligible else 'rolled_back' if was_active else 'awaiting_paired_evidence',
          'paired':len(window),'weeks':len(weeks[-12:]),'baseline_mae':round(b,3) if b is not None else None,
          'candidate_mae':round(c,3) if c is not None else None,'recent_paired':len(recent),
          'pick_checks':{k:{'games':n,'baseline_hits':base,'candidate_hits':cand} for k,(n,base,cand) in checks.items()}}
    return out


def main():
    target=json.loads(Path('data/live-v2.json').read_text()); season=int(target['season']);week=int(target['week'])
    schedules=nfl.load_schedules(list(range(2016,season+1))).to_dicts()
    _,fitted=train(schedules,season,week)
    models={}
    eligible=[(int(g['season']),int(g['week'])) for g in schedules if g.get('game_type')=='REG' and g.get('home_score') is not None and g.get('away_score') is not None and (int(g['season']),int(g['week']))<(season,week)]
    if not eligible:raise ValueError('No completed pre-target games; retaining previous runtime')
    year,last_week=max(eligible)
    for market,models_by_name in fitted.items():
        m=models_by_name['ml_ridge']; scaler=m.named_steps['standardscaler'];ridge=m.named_steps['ridge'];coef=ridge.coef_/scaler.scale_
        models[market]={'coefficients':[float(x) for x in coef],'intercept':float(ridge.intercept_-np.dot(coef,scaler.mean_)),'trained_season':year,'trained_week':last_week}
    if not models:raise ValueError('No game models trained; retaining previous runtime')
    def load(path,default):
        try:return json.loads(Path(path).read_text())
        except (OSError,ValueError):return default
    previous=load('data/game-ml-runtime.json',{})
    obs=load('data/game-pregame-observations.json',{}).get('records',[])
    results=load('data/game-official-results.json',{}).get('rows',[])
    decision=decide(pairs(obs,results),previous.get('decisions',{}) if previous.get('family')==FAMILY else {})
    for market in MARKETS:
        if market not in models:decision[market].update(active=False,reason='missing_model')
    result={'family':FAMILY,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'models':models,'decisions':decision,
            'policy':'100 matched games in six of last twelve weeks, 3% better MAE, no worse winner/ATS or OU hit rates on >=40 matched picks; rollback if evidence fails or recent MAE is 10% worse'}
    path=Path('data/game-ml-runtime.json');temp=path.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2)+'\n');temp.replace(path)
    print(json.dumps(decision,indent=2))
if __name__=='__main__': main()
