"""Generate same-refresh ML card candidates and grade frozen weekly batches.

Research display only: never edits production predictions or picks. A batch is
frozen at least 15 minutes before kickoff and evaluated only on verified finals.
"""
import csv, gzip, hashlib, json, math, zlib
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
from scripts.freeze_game_ml_predictions import train as train_games
from scripts.freeze_player_ml_predictions import fit as train_yards
from live.game_ml_runtime import game_features
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

DATA=Path('data')
NAMES=('ridge','random_forest','gradient_boosting','xgboost')
YARD_NAMES=NAMES+tuple(n+'_recent' for n in NAMES)+tuple(n+'_form' for n in NAMES)+tuple(n+'_form_recent' for n in NAMES)
COUNT_MAP={'player_pass_completions':'completions','player_rush_attempts':'carries','player_receptions':'receptions'}
YARDS={'passing_yards','rushing_yards','receiving_yards'}
GAME={'game_margin_home','game_total'}
REQUIRED_CURRENT=GAME|YARDS

def stamp(x):
    try:
        d=datetime.fromisoformat(str(x).replace('Z','+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (TypeError,ValueError): return None

def number(v):
    try:
        f=float(v)
        return f if math.isfinite(f) else None
    except (TypeError,ValueError): return None

def read(name,default):
    try: return json.loads((DATA/name).read_text())
    except (OSError,ValueError): return default

def gameweek(gid):
    try:
        a,b,*_=str(gid).split('_');return int(a),int(b)
    except (ValueError,TypeError): return None

def actuals(player_rows,game_rows):
    result={};conflicts=set()
    def add(k,v):
        if v is None:return
        if k in result and result[k]!=v:conflicts.add(k)
        result[k]=v
    for r in player_rows:
        if r.get('dnp') or r.get('played') is False:continue
        add((str(r.get('game_id')),str(r.get('player_id')),str(r.get('stat_key'))),number(r.get('actual')))
    for r in game_rows:
        h=number(r.get('home_score'));a=number(r.get('away_score'))
        if h is None or a is None:continue
        gid=str(r.get('game_id'))
        add((gid,'GAME','game_margin_home'),h-a);add((gid,'GAME','game_total'),h+a)
    for k in conflicts:result.pop(k,None)
    return result

def select(history, actual, target, versions=None):
    """Compare the exact same rows and same refresh; use latest completed week.

    Different markets may choose different algorithms. Missing data is not a
    vote: a model participates only where all four forecasts exist in one batch.
    """
    grouped=defaultdict(list)
    # A repeated identity is ambiguous; do not double-count or pick one copy.
    identities=defaultdict(int)
    for r in history:
        if isinstance(r,dict):identities[(str(r.get('game_id')),str(r.get('player_id')),str(r.get('market')))]+=1
    for r in history:
        try:
            if identities[(str(r.get('game_id')),str(r.get('player_id')),str(r.get('market')))]!=1:continue
            week=gameweek(r['game_id']);market=r['market'];p=r['predictions']
            kick=stamp(r['kickoff_utc']);captured=stamp(r['generated_at_utc'])
            val=actual.get((str(r['game_id']),str(r['player_id']),COUNT_MAP.get(market,market)))
            expected=(versions or {}).get(market,'same-refresh-v1')
            if r.get('model_version')!=expected or not week or week>=target or not kick or not captured or captured>kick-timedelta(minutes=15) or val is None:continue
            names=YARD_NAMES if market in YARDS and expected=='same-refresh-v2' else NAMES
            required=(*names,'current') if market in REQUIRED_CURRENT else names
            if set(p)!=set(required) or any(number(p[n]) is None for n in required):continue
            grouped[(week,market)].append((val,p))
        except (KeyError,TypeError):continue
    decisions={}
    for market in {m for _,m in grouped}:
        options=sorted((w,rows) for (w,m),rows in grouped.items() if m==market)
        week,rows=options[-1]
        expected=(target[0],target[1]-1) if target[1]>1 else (target[0]-1,18)
        if week!=expected:continue
        minimum=4 if market in GAME else 10
        if len(rows)<minimum:continue
        expected=(versions or {}).get(market,'same-refresh-v1')
        names=YARD_NAMES if market in YARDS and expected=='same-refresh-v2' else NAMES
        algorithms=(*names,'current') if market in REQUIRED_CURRENT else names
        errors={n:sum(abs(number(p[n])-v) for v,p in rows)/len(rows) for n in algorithms}
        # On an exact tie retain the existing card candidate.
        winner=min(algorithms,key=lambda n:(errors[n],0 if n=='current' else 1))
        decisions[market]={'model':winner,'season':week[0],'week':week[1],
                           'samples':len(rows),'mae':round(errors[winner],3),
                           'errors':{n:round(v,3) for n,v in errors.items()}}
    return decisions

def predict(models, features, names=NAMES):
    try:
        result={n:float(models[n].predict(np.asarray([features],dtype=float))[0]) for n in names}
        return result if all(math.isfinite(v) for v in result.values()) else None
    except (KeyError,TypeError,ValueError,OverflowError):return None

def predict_batch(models, vectors, names=NAMES):
    """Score each market as a batch; avoid fitting or traversing per player."""
    if not vectors:return {}
    try:
        x=np.asarray(vectors,dtype=float)
        if not np.isfinite(x).all():return None
        result={n:np.asarray(models[n].predict(x),dtype=float) for n in names}
        return result if all(len(v)==len(vectors) and np.isfinite(v).all() for v in result.values()) else None
    except (KeyError,TypeError,ValueError,OverflowError):return None

def load_yard_training(target):
    """Use the expanded archive only when its provenance and freshness verify."""
    path=DATA/'ml-card-training.csv.gz';meta=read('ml-card-training-meta.json',{})
    try:
        payload=path.read_bytes()
        if meta.get('schema_version')!=2 or hashlib.sha256(payload).hexdigest()!=meta.get('sha256'):
            raise ValueError('missing or mismatched history manifest')
        with gzip.open(path,'rt',encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
        eligible=[]
        for r in rows:
            try:
                key=(int(r['season']),int(r['week']))
                if key<target and r.get('market') in YARDS:eligible.append(r)
            except (KeyError,TypeError,ValueError):continue
        coverage={m:sum(r['market']==m for r in eligible) for m in YARDS}
        if len(rows)!=meta.get('rows') or not eligible or min(int(r['season']) for r in eligible)>2016 or min(coverage.values())<100:
            raise ValueError('history coverage is incomplete')
        latest={m:max((int(r['season']),int(r['week'])) for r in eligible if r['market']==m) for m in YARDS}
        def fresh(last):
            return (last[0]==target[0] and 0<target[1]-last[1]<=2) or (last[0]+1==target[0] and last[1]>=17 and target[1]<=2)
        if not all(fresh(value) for value in latest.values()):raise ValueError('history does not include recent completed weeks for every yard market')
        last=max(latest.values())
        return eligible,'same-refresh-v2',{'source':'2016-onward completed-game retrospective history',
            'seasons':sorted({int(r['season']) for r in eligible}), 'rows':len(eligible), 'archive_sha256':meta['sha256'],
            'latest_training_season':last[0],'latest_training_week':last[1],
            'inputs':['baseline','week','prior games','recent opportunities','recent yards','prior estimate']}
    except (OSError,ValueError,TypeError,KeyError,EOFError,csv.Error,zlib.error,OverflowError,AttributeError) as exc:
        print('Expanded player history unavailable; using existing fallback:',exc)
        with (DATA/'backtests/player-predictions.csv').open(newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
        return rows,'same-refresh-v1',{'source':'existing player backtest fallback'}

def train_yard_form(rows,target):
    """Prior-game form inputs are identical at training and live inference."""
    grouped=defaultdict(list)
    for r in rows:
        try:
            season,week=int(r['season']),int(r['week']);market=r['market']
            vec=[float(r['new']),float(r['old']),float(r['prior_games']),round(float(r['recent_volume']),1),float(r['recent_yards']),float(week)]
            y=float(r['actual'])
            if (season,week)>=target or market not in YARDS or not all(math.isfinite(x) and x>=0 for x in [*vec,y]):continue
            grouped[market].append((vec,y))
        except (KeyError,TypeError,ValueError):continue
    trained={}
    for market,items in grouped.items():
        if len(items)<100:continue
        x=np.array([item[0] for item in items]);y=np.array([item[1] for item in items])
        models={'ridge':make_pipeline(StandardScaler(),Ridge(alpha=100)),
          'random_forest':RandomForestRegressor(n_estimators=100,max_depth=5,min_samples_leaf=15,random_state=42,n_jobs=1),
          'gradient_boosting':HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=9,min_samples_leaf=25,l2_regularization=20,random_state=42),
          'xgboost':XGBRegressor(n_estimators=100,max_depth=3,learning_rate=.05,min_child_weight=15,reg_lambda=20,random_state=42,n_jobs=1,tree_method='hist')}
        for model in models.values():model.fit(x,y)
        trained[market]=models
    return trained

def live_form(p,week):
    try:
        last=[float(v) for v in p['last_5']]
        if not last:return None
        prior=[max(0,v) for v in last[-5:]]
        old=.55*sum(prior[-3:])/len(prior[-3:])+.45*sum(prior)/len(prior)
        vec=[float(p['projection']),round(old,1),float(p['games_used']),float(p['last_5_opportunities_avg']),round(sum(prior)/len(prior),3),float(week)]
        return vec if all(math.isfinite(v) and v>=0 for v in vec) and vec[2]>=3 else None
    except (KeyError,TypeError,ValueError,ZeroDivisionError):return None

def count_models(history,results,target):
    """Train from actually archived pregame live count estimates only."""
    actual=actuals(results,[]);training=defaultdict(list)
    identities=defaultdict(int)
    for r in history:
        if isinstance(r,dict) and r.get('model')=='live':identities[(str(r.get('game_id')),str(r.get('player_id')),str(r.get('stat_key')))]+=1
    for r in history:
        raw=r.get('stat_key');market=raw if raw in COUNT_MAP else next((k for k,v in COUNT_MAP.items() if v==raw),None);mapped=COUNT_MAP.get(market)
        if not mapped or r.get('model')!='live' or identities[(str(r.get('game_id')),str(r.get('player_id')),str(raw))]!=1:continue
        week=gameweek(r.get('game_id'));kick=stamp(r.get('kickoff_utc'));created=stamp(r.get('predicted_at_utc'))
        y=actual.get((str(r.get('game_id')),str(r.get('player_id')),mapped));x=number(r.get('projection'))
        if not week or week>=target or not kick or not created or created>=kick or x is None or y is None:continue
        training[market].append(([x,float(week[1])],y))
    trained={}
    for market,rows in training.items():
        if len(rows)<30 or len({int(row[0][1]) for row in rows})<2:continue
        x=np.array([r[0] for r in rows]);y=np.array([r[1] for r in rows])
        models={'ridge':make_pipeline(StandardScaler(),Ridge(alpha=100)),
          'random_forest':RandomForestRegressor(n_estimators=80,max_depth=4,min_samples_leaf=8,random_state=42,n_jobs=1),
          'gradient_boosting':HistGradientBoostingRegressor(max_iter=80,max_leaf_nodes=7,min_samples_leaf=8,l2_regularization=20,random_state=42),
          'xgboost':XGBRegressor(n_estimators=80,max_depth=3,learning_rate=.05,min_child_weight=8,reg_lambda=20,random_state=42,n_jobs=1,tree_method='hist')}
        for m in models.values():m.fit(x,y)
        trained[market]=models
    return trained

def run(now=None):
    import nflreadpy as nfl
    realtime=now is None
    now=now or datetime.now(timezone.utc)
    live=read('live-v2.json',{});players=read('player-research.json',{});counts=read('count-projections.json',{})
    season=int(live['season']);week=int(live['week']);target=(season,week)
    if (players.get('season'),players.get('week'))!=target:raise ValueError('Player feed does not match forecast slate')
    live_time=stamp(live.get('generated_at_utc'));player_time=stamp(players.get('generated_at_utc'))
    if not live_time or not player_time or live_time>now or player_time>now:raise ValueError('Invalid forecast timestamps')
    prior=read('ml-card-batches.json',{}).get('rows',[])
    finals=actuals(read('player-results.json',{}).get('rows',[]),read('game-official-results.json',{}).get('rows',[]))
    yard_rows,yard_version,yard_coverage=load_yard_training(target)
    versions={market:yard_version for market in YARDS}
    decisions=select(prior,finals,target,versions)
    schedule=nfl.load_schedules(list(range(2016,season+1))).to_dicts()
    _,games=train_games(schedule,season,week)
    game_models={m:{n:models['ml_'+n] for n in NAMES} for m,models in games.items()}
    yards=train_yards(yard_rows,target)
    yard_forms={};recent_forms={}
    if yard_version=='same-refresh-v2':
        yard_forms=train_yard_form(yard_rows,target)
        recent=[r for r in yard_rows if int(r['season'])>=season-2]
        recent_models=train_yards(recent,target)
        recent_forms=train_yard_form(recent,target)
        for market in list(yards):
            if market not in recent_models or market not in yard_forms or market not in recent_forms:
                del yards[market]
                continue
            yards[market].update({name+'_recent':model for name,model in recent_models[market].items()})
    count=count_models(read('weekly-shadow-forecasts.json',{}).get('rows',[]),read('player-results.json',{}).get('rows',[]),target)
    games_by_id={str(g.get('game_id')):g for g in live.get('games',[])}
    candidates=[]
    def add(gid,pid,market,values,kick,current=None):
        if values is None or not kick or now>=kick:return
        if market in REQUIRED_CURRENT:
            incumbent=number(current)
            if incumbent is None:return
            values={**values,'current':incumbent}
        candidates.append({'game_id':gid,'player_id':pid,'market':market,
            'predictions':{n:round(max(0,v) if market!='game_margin_home' else v,3) for n,v in values.items()},
            'generated_at_utc':now.isoformat(),'kickoff_utc':kick.isoformat(),
            'model_version':versions.get(market,'same-refresh-v1'),
            'training_archive_sha256':yard_coverage.get('archive_sha256') if market in YARDS else None})
    for gid,g in games_by_id.items():
        kick=stamp(g.get('kickoff_utc'));features=game_features(g)
        if not features:continue
        for market in GAME:
            if market in game_models:
                incumbent=(g.get('game_ml_shadow') or {}).get('markets',{}).get(market,{})
                add(gid,'GAME',market,predict(game_models[market],features),kick,incumbent.get('candidate'))
    player_groups=defaultdict(list)
    for p in players.get('players',[]):
        gid=str(p.get('game_id'));pid=str(p.get('player_id') or '');market=p.get('stat_key');base=number(p.get('projection'))
        g=games_by_id.get(gid);incumbent=(p.get('player_ml_shadow') or {}).get('candidate')
        if not g or not pid or market not in YARDS or market not in yards or base is None or base<0 or number(incumbent) is None:continue
        features=live_form(p,week) if yard_version=='same-refresh-v2' else None
        if yard_version=='same-refresh-v2' and features is None:continue
        player_groups[market].append((gid,pid,g,incumbent,[base,float(week)],features))
    for market,group in player_groups.items():
        names=NAMES+tuple(n+'_recent' for n in NAMES) if yard_version=='same-refresh-v2' else NAMES
        simple=predict_batch(yards[market],[p[4] for p in group],names)
        if simple is None:continue
        if yard_version=='same-refresh-v2':
            form=predict_batch(yard_forms[market],[p[5] for p in group])
            form_recent=predict_batch(recent_forms[market],[p[5] for p in group])
            if form is None or form_recent is None:continue
        for i,(gid,pid,g,incumbent,_,_) in enumerate(group):
            values={n:float(simple[n][i]) for n in names}
            if yard_version=='same-refresh-v2':
                values.update({n+'_form':float(form[n][i]) for n in NAMES})
                values.update({n+'_form_recent':float(form_recent[n][i]) for n in NAMES})
            add(gid,pid,market,values,stamp(g.get('kickoff_utc')),incumbent)
    if (counts.get('season'),counts.get('week'))==target and stamp(counts.get('generated_at_utc')) and stamp(counts['generated_at_utc'])<=now:
        count_groups=defaultdict(list)
        for p in counts.get('players',[]):
            gid=str(p.get('game_id'));pid=str(p.get('player_id') or '');market=p.get('market_key');base=number(p.get('projection'));g=games_by_id.get(gid)
            if not g or not pid or market not in count or base is None or base<0:continue
            count_groups[market].append((gid,pid,g,[base,float(week)]))
        for market,group in count_groups.items():
            scored=predict_batch(count[market],[r[3] for r in group])
            if scored is None:continue
            for i,(gid,pid,g,_) in enumerate(group):
                add(gid,pid,market,{n:float(scored[n][i]) for n in NAMES},stamp(g.get('kickoff_utc')))
    # Use the actual completion time, not the time before model training began.
    finished=datetime.now(timezone.utc) if realtime else now
    candidates=[r for r in candidates if finished<stamp(r['kickoff_utc'])]
    identities=defaultdict(int)
    for r in candidates:identities[(r['game_id'],r['player_id'],r['market'])]+=1
    candidates=[r for r in candidates if identities[(r['game_id'],r['player_id'],r['market'])]==1]
    # Freeze the chosen algorithm as well as the values. Do not replace either
    # after the T-15 cutoff, even if another refresh or results arrive.
    stored={(r['game_id'],r['player_id'],r['market']):r for r in prior}
    display=[]
    for row in candidates:
        row['generated_at_utc']=finished.isoformat()
        row['selected']=decisions.get(row['market'])
        key=(row['game_id'],row['player_id'],row['market'])
        if finished<=stamp(row['kickoff_utc'])-timedelta(minutes=15):
            stored[key]=row
            display.append(row)
        elif key in stored and stored[key].get('model_version') in ('same-refresh-v1','same-refresh-v2'):
            display.append(stored[key])
    candidates=display
    out={'schema_version':1,'research_only':True,'season':season,'week':week,
         'generated_at_utc':finished.isoformat(),'forecast_generated_at_utc':live.get('generated_at_utc'),
         'player_generated_at_utc':players.get('generated_at_utc'),
         'count_generated_at_utc':counts.get('generated_at_utc'),
         'training_coverage':{'player_yards':yard_coverage},
         'decisions':decisions,'candidates':candidates}
    for name,obj in [('ml-card-rotation.json',out),('ml-card-batches.json',{'schema_version':1,'rows':list(stored.values())})]:
        path=DATA/name;tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(obj,indent=2)+'\n');tmp.replace(path)
    print('ML card batch:',len(candidates),'candidates;',len(decisions),'weekly selections')
if __name__=='__main__':run()
