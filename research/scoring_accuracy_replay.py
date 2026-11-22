#!/usr/bin/env python3
"""Paired, strictly prior-week scoring research; never changes live projections."""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backtest.v2 import build_v2_predictions

PARAMETERS = {
    'v2': (4.0, 4.0), 'less_shrinkage': (4.0, 2.0),
    'more_shrinkage': (4.0, 6.0), 'faster_recency': (2.0, 4.0),
    'slower_recency': (8.0, 4.0),
}


def metrics(pairs):
    if not pairs:
        return {'samples': 0, 'mae': None, 'rmse': None, 'bias': None}
    errors = [p - a for p, a in pairs]
    return {'samples': len(errors), 'mae': round(sum(map(abs, errors))/len(errors), 3),
            'rmse': round(math.sqrt(sum(e*e for e in errors)/len(errors)), 3),
            'bias': round(sum(errors)/len(errors), 3)}


def valid_number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def replay(schedules, team_games, weekly):
    """Features supplied for each (season, week, team) contain that week's data.

    Construct every target's inputs from completed prior weeks only. Fit model
    coefficients only on games in seasons/weeks strictly earlier than target.
    """
    completed = [g for g in schedules if g.get('game_type') == 'REG'
                 and valid_number(g.get('home_score')) is not None
                 and valid_number(g.get('away_score')) is not None]
    projections = {name: {p['game_id']: p for p in build_v2_predictions(
        completed, team_games, half_life=half, prior_weight=prior)}
        for name, (half, prior) in PARAMETERS.items()}
    weekly_index = defaultdict(list)
    for row in weekly:
        weekly_index[(int(row['season']), row['team'])].append(row)
    def history(season, week, team):
        rows = sorted((r for r in weekly_index[(season, team)] if int(r['week']) < week),
                      key=lambda r: int(r['week']))[-5:]
        if len(rows) < 3:
            return None
        result = []
        for key in ('plays', 'pass_rate', 'pass_off', 'rush_off', 'pass_def', 'rush_def'):
            values = [valid_number(r.get(key)) for r in rows]
            values = [v for v in values if v is not None]
            if not values:
                return None
            result.append(sum(values) / len(values))
        return result
    rows = []
    for game in sorted(completed, key=lambda g:(int(g['season']),int(g['week']),g['game_id'])):
        gid = game['game_id']; season = int(game['season']); week = int(game['week'])
        if any(gid not in projections[name] for name in PARAMETERS):
            continue
        home = history(season, week, game['home_team']); away = history(season, week, game['away_team'])
        if home is None or away is None:
            continue
        baseline = projections['v2'][gid]
        rows.append({'season': season, 'week': week, 'game_id': gid,
                     'actual_margin': baseline['actual_margin'], 'actual_total': baseline['actual_total'],
                     'basic': [baseline['pred_margin'], baseline['pred_total'], week],
                     'expanded': [baseline['pred_margin'], baseline['pred_total'], week] + home + away,
                     'market_margin': -valid_number(game['spread_line']) if valid_number(game.get('spread_line')) is not None else None,
                     'market_total': valid_number(game.get('total_line')),
                     'predictions': {n: {'margin':projections[n][gid]['pred_margin'],
                                         'total':projections[n][gid]['pred_total']} for n in PARAMETERS}})
    for season, week in sorted({(r['season'], r['week']) for r in rows}):
        train = [r for r in rows if (r['season'], r['week']) < (season, week)]
        test = [r for r in rows if (r['season'], r['week']) == (season, week)]
        if len(train) < 150:
            continue
        for feature in ('basic', 'expanded'):
            X = np.asarray([r[feature] for r in train], dtype=float)
            XT = np.asarray([r[feature] for r in test], dtype=float)
            for market in ('margin', 'total'):
                model = make_pipeline(StandardScaler(), Ridge(alpha=100.0))
                model.fit(X, [r['actual_'+market] for r in train])
                for row, prediction in zip(test, model.predict(XT)):
                    row['predictions'].setdefault('ridge_'+feature, {})[market] = float(prediction)
    return rows


def report(rows):
    # Compare all candidates on the same games where both ridge models ran.
    rows = [r for r in rows if 'ridge_expanded' in r['predictions']]
    result = {'status':'research_only', 'production_modified':False,
              'method':'Predeclared variants; features and ridge training use earlier weeks only. Same games for all models.',
              'limitations':['V2 replay excludes live QB adjustments; it is a comparison proxy, not the exact published forecast.',
                  'Historical spread and total are schedule-market references, not verified DK opening or pregame prices; closing information may be later than model forecasts.',
                  'No verified time-stamped historical pregame weather, QB starter or injury status was included; no causal claims or production promotion.',
                  'Selection on these results requires a separate prospective or untouched holdout evaluation.'],
              'seasons':{}, 'models':{}, 'market_reference':{}}
    names = list(PARAMETERS) + ['ridge_basic', 'ridge_expanded']
    def summarize(subset):
        out = {}
        for name in names:
            d = {}
            for market in ('margin','total'):
                d[market] = metrics([(r['predictions'][name][market],r['actual_'+market]) for r in subset])
            d['team_score'] = metrics([(p,a) for r in subset for p,a in [
                ((r['predictions'][name]['total']+r['predictions'][name]['margin'])/2,(r['actual_total']+r['actual_margin'])/2),
                ((r['predictions'][name]['total']-r['predictions'][name]['margin'])/2,(r['actual_total']-r['actual_margin'])/2)]])
            out[name] = d
        return out
    result['models'] = summarize(rows)
    for season in sorted({r['season'] for r in rows}):
        result['seasons'][str(season)] = summarize([r for r in rows if r['season']==season])
    for market in ('margin','total'):
        subset = [r for r in rows if r['market_'+market] is not None]
        result['market_reference'][market] = {
            'market':metrics([(r['market_'+market],r['actual_'+market]) for r in subset]),
            'v2_same_games':metrics([(r['predictions']['v2'][market],r['actual_'+market]) for r in subset])}
    result['eligible_games'] = len(rows)
    return result


def load_season(nfl, season):
    import polars as pl
    schedules = nfl.load_schedules([season]).to_dicts()
    pbp = nfl.load_pbp([season]).select(['season','week','game_id','play_type','posteam','defteam','epa'])
    pbp = pbp.filter(pl.col('play_type').is_in(['pass','run']) & pl.col('epa').is_not_null()
                     & pl.col('posteam').is_not_null() & pl.col('defteam').is_not_null())
    keys = ['season','week','game_id']
    off = pbp.group_by(keys+['posteam']).agg(pl.col('epa').mean().alias('offense_epa'),
        pl.len().alias('plays'), (pl.col('play_type')=='pass').mean().alias('pass_rate'),
        pl.col('epa').filter(pl.col('play_type')=='pass').mean().alias('pass_off'),
        pl.col('epa').filter(pl.col('play_type')=='run').mean().alias('rush_off')).rename({'posteam':'team'})
    defense = pbp.group_by(keys+['defteam']).agg(pl.col('epa').mean().alias('defense_epa'),
        pl.col('epa').filter(pl.col('play_type')=='pass').mean().alias('pass_def'),
        pl.col('epa').filter(pl.col('play_type')=='run').mean().alias('rush_def')).rename({'defteam':'team'})
    aggregate = off.join(defense,on=keys+['team'],how='inner').to_dicts()
    completed = {g['game_id'] for g in schedules if g.get('game_type')=='REG'
                 and valid_number(g.get('home_score')) is not None and valid_number(g.get('away_score')) is not None}
    aggregate = [r for r in aggregate if r['game_id'] in completed]
    return schedules, aggregate, aggregate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start',type=int,default=2016)
    parser.add_argument('--end',type=int,default=2025)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.start > args.end:
        parser.error('start season must not follow end season')
    import nflreadpy as nfl
    schedules=[]; teams=[]; weekly=[]; coverage={}
    for year in range(args.start,args.end+1):
        print('Loading season',year,flush=True)
        s,t,w=load_season(nfl,year)
        schedules.extend(s); teams.extend(t); weekly.extend(w)
        coverage[str(year)]={'schedules':len(s),'team_games':len(t)}
    result=report(replay(schedules,teams,weekly)); result['coverage']=coverage
    if result['eligible_games'] < 200:
        raise RuntimeError('Insufficient matched historical games')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)

if __name__ == '__main__':
    main()
