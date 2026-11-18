"""Generate same-refresh ML card candidates and grade frozen weekly batches.

Research display only: never edits production predictions or picks. A batch is
frozen at least 15 minutes before kickoff and evaluated only on verified finals.
"""
import csv, json, math
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

def select(history, actual, target):
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
            if r.get('model_version')!='same-refresh-v1' or not week or week>=target or not kick or not captured or captured>kick-timedelta(minutes=15) or val is None:continue
            required=(*NAMES,'current') if market in REQUIRED_CURRENT else NAMES
            if set(p)!=set(required) or any(number(p[n]) is None for n in required):continue
            grouped[(week,market)].append((val,p))
        except (KeyError,TypeError):continue
    decisions={}
    for market in {m for _,m in grouped}:
        options=sorted((w,rows) for (w,m),rows in grouped.items() if m==market)
        week,rows=options[-1]
        minimum=4 if market in GAME else 10
        if len(rows)<minimum:continue
        algorithms=(*NAMES,'current') if market in REQUIRED_CURRENT else NAMES
        errors={n:sum(abs(number(p[n])-v) for v,p in rows)/len(rows) for n in algorithms}
        # On an exact tie retain the existing card candidate.
        winner=min(algorithms,key=lambda n:(errors[n],0 if n=='current' else 1))
        decisions[market]={'model':winner,'season':week[0],'week':week[1],
                           'samples':len(rows),'mae':round(errors[winner],3),
                           'errors':{n:round(v,3) for n,v in errors.items()}}
    return decisions

def predict(models, features):
    try:
        result={n:float(models[n].predict(np.asarray([features],dtype=float))[0]) for n in NAMES}
        return result if all(math.isfinite(v) for v in result.values()) else None
    except (KeyError,TypeError,ValueError,OverflowError):return None

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
    decisions=select(prior,finals,target)
    schedule=nfl.load_schedules(list(range(2016,season+1))).to_dicts()
    _,games=train_games(schedule,season,week)
    game_models={m:{n:models['ml_'+n] for n in NAMES} for m,models in games.items()}
    with (DATA/'backtests/player-predictions.csv').open(newline='') as f:yards=train_yards(csv.DictReader(f),target)
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
            'generated_at_utc':now.isoformat(),'kickoff_utc':kick.isoformat(),'model_version':'same-refresh-v1'})
    for gid,g in games_by_id.items():
        kick=stamp(g.get('kickoff_utc'));features=game_features(g)
        if not features:continue
        for market in GAME:
            if market in game_models:
                incumbent=(g.get('game_ml_shadow') or {}).get('markets',{}).get(market,{})
                add(gid,'GAME',market,predict(game_models[market],features),kick,incumbent.get('candidate'))
    for p in players.get('players',[]):
        gid=str(p.get('game_id'));pid=str(p.get('player_id') or '');market=p.get('stat_key');base=number(p.get('projection'))
        g=games_by_id.get(gid)
        if not g or not pid or market not in YARDS or market not in yards or base is None:continue
        incumbent=(p.get('player_ml_shadow') or {}).get('candidate')
        add(gid,pid,market,predict(yards[market],[base,float(week)]),stamp(g.get('kickoff_utc')),incumbent)
    if (counts.get('season'),counts.get('week'))==target and stamp(counts.get('generated_at_utc')) and stamp(counts['generated_at_utc'])<=now:
        for p in counts.get('players',[]):
            gid=str(p.get('game_id'));pid=str(p.get('player_id') or '');market=p.get('market_key');base=number(p.get('projection'));g=games_by_id.get(gid)
            if not g or not pid or market not in count or base is None:continue
            add(gid,pid,market,predict(count[market],[base,float(week)]),stamp(g.get('kickoff_utc')))
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
        elif key in stored and stored[key].get('model_version')=='same-refresh-v1':
            display.append(stored[key])
    candidates=display
    out={'schema_version':1,'research_only':True,'season':season,'week':week,
         'generated_at_utc':finished.isoformat(),'forecast_generated_at_utc':live.get('generated_at_utc'),
         'player_generated_at_utc':players.get('generated_at_utc'),
         'count_generated_at_utc':counts.get('generated_at_utc'),
         'decisions':decisions,'candidates':candidates}
    for name,obj in [('ml-card-rotation.json',out),('ml-card-batches.json',{'schema_version':1,'rows':list(stored.values())})]:
        path=DATA/name;tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(obj,indent=2)+'\n');tmp.replace(path)
    print('ML card batch:',len(candidates),'candidates;',len(decisions),'weekly selections')
if __name__=='__main__':run()
