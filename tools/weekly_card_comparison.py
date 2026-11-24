"""Grade saved card estimates against verified results, never reconstruct forecasts."""
import json
import math
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA = Path('data')
MARKETS = {'player_pass_yds': 'passing_yards', 'player_rush_yds': 'rushing_yards',
           'player_rec_yds': 'receiving_yards', 'player_pass_completions': 'completions',
           'player_rush_attempts': 'carries', 'player_receptions': 'receptions',
           'player_pass_attempts': 'attempts'}
BATCH_MARKETS = {'completions':'player_pass_completions','carries':'player_rush_attempts',
                 'receptions':'player_receptions','attempts':'player_pass_attempts'}
LABELS = {'game_margin_home': 'Game margin', 'game_total': 'Game total',
          'passing_yards': 'Passing yards', 'rushing_yards': 'Rushing yards',
          'receiving_yards': 'Receiving yards', 'completions': 'Completions',
          'carries': 'Rush attempts', 'receptions': 'Receptions', 'attempts':'Pass attempts'}

def number(value):
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None

def stamp(value):
    try:
        d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return d if d.tzinfo else None
    except (ValueError, TypeError):
        return None

def unique_map(rows, key):
    out, duplicates = {}, set()
    for row in rows:
        k = key(row)
        if k in out and out[k] != row: duplicates.add(k)
        else: out[k] = row
    return {k: v for k, v in out.items() if k not in duplicates}

def batch_value(batch, incumbent, forecast_at, saved_at, kickoff):
    """Only use the same saved candidate as the captured source feed."""
    generated = stamp(batch.get('generated_at_utc')) if batch else None
    if not generated or not forecast_at or not saved_at or not (forecast_at <= generated <= saved_at < kickoff): return None
    if batch.get('published_at_utc') is not None:
        published=stamp(batch['published_at_utc'])
        if not published or not (generated<=published<=saved_at): return None
    if saved_at - generated > timedelta(hours=120): return None
    predictions = batch.get('predictions') or {}
    current = number(predictions.get('current'))
    # Some count markets have no incumbent: the selected model must be saved.
    if incumbent is not None and (current is None or abs(current - incumbent) > .11): return None
    selected = batch.get('selected') or {}
    model = selected.get('model')
    if not model: return (current, 'Existing ML estimate') if current is not None else None
    if model == 'current': return (current, 'Existing ML estimate') if current is not None else None
    valid_models={n+s for n in ('ridge','random_forest','gradient_boosting','xgboost') for s in ('','_recent','_form','_form_recent')}
    minimum=4 if str(batch.get('player_id'))=='GAME' else 10
    if model not in valid_models or not isinstance(selected.get('samples'),int) or selected['samples']<minimum: return None
    value = number(predictions.get(model))
    return (value, model.replace('_', ' ')) if value is not None else None

def saved_batch_value(batches, incumbent, forecast_at, saved_at, kickoff):
    """Choose the latest unambiguous batch that existed at snapshot time."""
    eligible=[]
    for batch in batches:
        value=batch_value(batch,incumbent,forecast_at,saved_at,kickoff)
        if value is not None:
            eligible.append((stamp(batch['generated_at_utc']),value))
    if not eligible:return None
    latest=max(t for t,_ in eligible)
    values={value for t,value in eligible if t==latest}
    return next(iter(values)) if len(values)==1 else None

def build(game_results, locks, player_results, snapshots, history, batches):
    games = unique_map(game_results, lambda r: str(r.get('game_id')))
    locks = unique_map(locks, lambda r: str(r.get('game_id')))
    batch_versions = defaultdict(list)
    for row in batches:
        batch_versions[(str(row.get('game_id')),str(row.get('player_id')),str(row.get('market')))].append(row)
    actuals = unique_map([r for r in player_results if not r.get('dnp') and r.get('played') is not False],
                         lambda r: (str(r.get('game_id')), str(r.get('player_id')), str(r.get('stat_key'))))
    # Different line observations can accompany exactly the same published forecast.
    hist = defaultdict(list)
    for h in history:
        key = (str(h.get('game_id')), str(h.get('player_id')), str(h.get('stat_key')), str(h.get('forecast_captured_at_utc')))
        hist[key].append(h)
    byweek = defaultdict(list)
    shadow_byweek = defaultdict(list)
    def add(gid, market, name, actual, regular, ml, model):
        try: season, week = map(int, gid.split('_')[:2])
        except (ValueError, AttributeError): return
        if None in (actual, regular, ml): return
        re, me = abs(regular-actual), abs(ml-actual)
        byweek[(season, week)].append({'game_id':gid, 'market':market, 'label':name,
            'actual':round(actual, 2), 'regular':round(regular, 2), 'ml':round(ml, 2),
            'regular_error':round(re, 2), 'ml_error':round(me, 2),
            'winner':'tie' if abs(re-me)<.05 else 'regular' if re<me else 'ml', 'ml_model':model})
    for gid, result in games.items():
        lock=locks.get(gid) or {}; kick=stamp(lock.get('kickoff_utc')); captured=stamp(lock.get('captured_at_utc')); forecast=stamp(lock.get('forecast_at_utc'))
        home,away=number(result.get('home_score')),number(result.get('away_score'))
        if not kick or not captured or not forecast or not (forecast <= captured < kick) or home is None or away is None: continue
        for market, actual, field in [('game_margin_home',home-away,'projected_margin_home'),('game_total',home+away,'projected_total')]:
            raw=(lock.get('game_ml_shadow') or {}).get('markets',{}).get(market,{})
            incumbent=number(raw.get('candidate')); batch=batch_versions.get((gid,'GAME',market),[])
            regular=number(lock.get(field))
            if incumbent is not None and regular is not None:
                try:
                    season, week = map(int, gid.split('_')[:2])
                except (ValueError, AttributeError):
                    continue
                shadow_byweek[(season,week)].append({
                    'game_id':gid, 'market':market, 'actual':actual,
                    'regular':regular, 'shadow':incumbent,
                    'regular_error':round(abs(regular-actual),2),
                    'shadow_error':round(abs(incumbent-actual),2),
                    'lock_status':lock.get('lock_status'),
                    'captured_at_utc':lock.get('captured_at_utc')})
            if lock.get('lock_status') not in ('official','last_available','forecast_only'): continue
            ml=saved_batch_value(batch,incumbent,forecast,captured,kick) if batch and incumbent is not None else None
            if ml: add(gid,market,f"{lock.get('away')} @ {lock.get('home')}",actual,number(lock.get(field)),ml[0],ml[1])
    unique_snapshots=unique_map(snapshots,lambda r:(str(r.get('game_id')),str(r.get('player_id')),str(r.get('market'))))
    for s in unique_snapshots.values():
        gid=str(s.get('game_id')); pid=str(s.get('player_id')); market=MARKETS.get(s.get('market'))
        if not market: continue
        actual=actuals.get((gid,pid,market)); kick=stamp(s.get('kickoff')); forecast=stamp(s.get('captured_at')); saved=stamp(s.get('saved_at_utc'))
        if not actual or not kick or not forecast or not saved or not (forecast<=saved<kick): continue
        regular=number(s.get('projection'))
        if regular is None or number(actual.get('projection')) is None or abs(regular-number(actual['projection']))>.11: continue
        matches=[h for h in hist.get((gid,pid,market,str(s.get('captured_at'))),[]) if number(h.get('projection')) is not None and abs(number(h['projection'])-regular)<.11 and stamp(h.get('saved_at_utc')) and stamp(h['saved_at_utc'])<kick]
        shadows={number((h.get('player_ml_shadow') or {}).get('candidate')) for h in matches}
        shadows.discard(None)
        if len(shadows)>1: continue
        incumbent=next(iter(shadows),None); batch=batch_versions.get((gid,pid,BATCH_MARKETS.get(market,market)),[])
        ml=saved_batch_value(batch,incumbent,forecast,saved,kick) if batch and (incumbent is not None or market in BATCH_MARKETS) else None
        if ml: add(gid,market,str(s.get('player') or pid),number(actual.get('actual')),regular,ml[0],ml[1])
    weeks=[]
    for (season,week), rows in sorted(byweek.items(),reverse=True):
        groups=[]
        for market,label in LABELS.items():
            items=[r for r in rows if r['market']==market]
            if not items: continue
            reg=sum(r['regular_error'] for r in items)/len(items); ml=sum(r['ml_error'] for r in items)/len(items)
            groups.append({'market':market,'label':label,'samples':len(items),'regular_mae':round(reg,2),'ml_mae':round(ml,2),
                'winner':'tie' if abs(reg-ml)<.005 else 'regular' if reg<ml else 'ml',
                'regular_wins':sum(r['winner']=='regular' for r in items),'ml_wins':sum(r['winner']=='ml' for r in items),
                'ties':sum(r['winner']=='tie' for r in items),'details':items})
        weeks.append({'season':season,'week':week,'markets':groups})
    shadow_weeks=[]
    for (season,week), rows in sorted(shadow_byweek.items(),reverse=True):
        markets=[]
        for market in ('game_margin_home','game_total'):
            items=[row for row in rows if row['market']==market]
            if not items: continue
            markets.append({'market':market,'samples':len(items),
                'regular_mae':round(sum(r['regular_error'] for r in items)/len(items),2),
                'shadow_mae':round(sum(r['shadow_error'] for r in items)/len(items),2),
                'details':items})
        shadow_weeks.append({'season':season,'week':week,'markets':markets})
    return {'generated_at_utc':datetime.now(timezone.utc).isoformat(),'weeks':weeks,
      'game_shadow_comparisons':shadow_weeks,
      'game_shadow_note':'Saved game-lock shadow candidates, including early locks; these are not necessarily the selected ML card model.',
      'note':'Only matched, saved pregame card estimates with verified final results; incomplete markets remain absent.'}

def main():
    def read(name, key):
        value=json.loads((DATA/name).read_text()).get(key)
        if not isinstance(value,list): raise ValueError(f'Invalid {name}: missing {key} list')
        return value
    history_path=DATA/'ml-card-batch-history.json'
    historical=read('ml-card-batch-history.json','rows') if history_path.exists() else []
    if (DATA/'ml-card-batch-recovered.json').exists():
        historical+=read('ml-card-batch-recovered.json','rows')
    report=build(read('game-official-results.json','rows'),read('game-official-pregame-locks.json','records'),
      read('player-results.json','rows'),read('pregame-snapshots.json','records'),read('player-history.json','players'),historical+read('ml-card-batches.json','rows'))
    (DATA/'weekly-card-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Weekly matched card comparisons:',[(w['season'],w['week'],sum(m['samples'] for m in w['markets'])) for w in report['weeks']])

if __name__=='__main__': main()
