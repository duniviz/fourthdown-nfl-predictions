"""Walk-forward, paired scoring ablation; never publishes a production model."""
import gc
import csv
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

import nflreadpy as nfl
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from research.coach_matchup_context import build
from research.expanded_game_feature_lab import features


def evaluate(rows):
    out = []
    for season in (2024, 2025, 2026):
        train = [r for r in rows if r['season'] < season]
        test = [r for r in rows if r['season'] == season]
        if len(train) < 100 or len(test) < 20:
            continue
        for market in ('total', 'margin'):
            actual = np.array([r[market] for r in test])
            predictions = {}
            for group in ('baseline', 'coach', 'defense', 'combined'):
                def vector(r):
                    return r['base'] + (r['coach'] if group in ('coach', 'combined') else []) + (r['defense'] if group in ('defense', 'combined') else [])
                model = make_pipeline(StandardScaler(), Ridge(alpha=100))
                model.fit(np.array([vector(r) for r in train]), np.array([r[market] for r in train]))
                predictions[group] = model.predict(np.array([vector(r) for r in test]))
            base_mae = float(np.mean(abs(predictions['baseline'] - actual)))
            for group, predicted in predictions.items():
                mae = float(np.mean(abs(predicted - actual)))
                out.append({'season': season, 'market': market, 'variant': group,
                            'training_games': len(train), 'matched_games': len(test),
                            'mae': round(mae, 4), 'baseline_mae': round(base_mae, 4),
                            'improvement_pct': round(100 * (base_mae - mae) / base_mae, 3)})
    return out


def evaluate_players(rows):
    out = []
    for season in (2024, 2025, 2026):
        for market in ('passing_yards', 'rushing_yards', 'receiving_yards'):
            train = [r for r in rows if r['season'] < season and r['market'] == market]
            test = [r for r in rows if r['season'] == season and r['market'] == market]
            if len(train) < 100 or len(test) < 20:
                continue
            actual = np.array([r['actual'] for r in test])
            predictions = {}
            for group in ('baseline', 'coach', 'defense', 'combined'):
                def vector(r):
                    return r['base'] + (r['coach'] if group in ('coach', 'combined') else []) + (r['defense'] if group in ('defense', 'combined') else [])
                model = make_pipeline(StandardScaler(), Ridge(alpha=100))
                model.fit(np.array([vector(r) for r in train]), np.array([r['actual'] for r in train]))
                predictions[group] = model.predict(np.array([vector(r) for r in test]))
            base_mae = float(np.mean(abs(predictions['baseline'] - actual)))
            for group, predicted in predictions.items():
                mae = float(np.mean(abs(predicted - actual)))
                out.append({'season': season, 'market': market, 'variant': group,
                            'training_rows': len(train), 'matched_rows': len(test),
                            'mae': round(mae, 4), 'baseline_mae': round(base_mae, 4),
                            'improvement_pct': round(100 * (base_mae - mae) / base_mae, 3)})
    return out


def match_players(year, source, stats, games, context):
    game_by_id = {str(g['game_id']): g for g in games}
    identities = {}
    for row in stats:
        try:
            key = (int(row['season']), int(row['week']), str(row['player_id']))
            ident = (str(row['game_id']), str(row['team']))
            if key in identities:
                identities[key] = None
            else:
                identities[key] = ident
        except (KeyError, TypeError, ValueError):
            continue
    matched = []
    for raw in source:
        try:
            if int(raw['season']) != year:
                continue
            week = int(raw['week'])
            ident = identities.get((year, week, str(raw['player_id'])))
            if not ident:
                continue
            gid, team = ident
            game, ctx = game_by_id.get(gid), context.get(gid)
            if not game or not ctx or team not in (game['home_team'], game['away_team']):
                continue
            # Order features consistently: player team first, opponent second.
            home = team == game['home_team']
            c, d = ctx['coach'], ctx['defense']
            cf = [c[0], c[1], c[2], c[3]] if home else [c[1], c[0], c[3], c[2]]
            df = [d[0], d[1], d[2], d[3]] if home else [d[1], d[0], d[3], d[2]]
            base = [float(raw[k]) for k in ('new', 'old', 'prior_games', 'recent_volume', 'recent_yards')]+[float(week)]
            actual = float(raw['actual'])
            if not all(np.isfinite(x) for x in base + [actual]):
                continue
            matched.append({'season': year, 'market': raw['market'], 'base': base,
                            'coach': cf, 'defense': df, 'actual': actual})
        except (KeyError, TypeError, ValueError):
            continue
    return matched


def main():
    years = list(range(2019, datetime.now(timezone.utc).year + 1))
    schedules = nfl.load_schedules(years).to_dicts()
    with gzip.open('data/ml-card-training.csv.gz', 'rt', encoding='utf-8', newline='') as f:
        player_source = list(csv.DictReader(f))
    rows, player_rows, coverage = [], [], {}
    for year in years:
        games = [g for g in schedules if g.get('season') == year]
        try:
            frame = nfl.load_pbp([year])
            columns = ['game_id', 'season', 'week', 'season_type', 'play_type', 'posteam', 'defteam',
                       'epa', 'success', 'yardline_100', 'cpoe', 'score_differential', 'yards_gained']
            plays = frame.select(columns).to_dicts()
            ctx = build(games, plays)
            base = features(games, plays)
            matched = [dict(r, **ctx[r['game_id']]) for r in base if r['game_id'] in ctx]
            rows.extend(matched)
            stats = nfl.load_player_stats([year], summary_level='week').select(['season', 'week', 'player_id', 'game_id', 'team']).to_dicts()
            player_matched = match_players(year, player_source, stats, games, ctx)
            player_rows.extend(player_matched)
            coverage[str(year)] = {'plays': len(plays), 'baseline_games': len(base), 'matched_games': len(matched),
                                   'matched_player_rows': len(player_matched)}
            del frame, plays, base, ctx, matched
            gc.collect()
        except Exception as exc:
            coverage[str(year)] = {'error': f'{type(exc).__name__}: {exc}'}
            print('Unavailable season:', year, type(exc).__name__, str(exc), flush=True)
    results, player_results = evaluate(rows), evaluate_players(player_rows)
    if not results or not player_results:
        raise RuntimeError('Insufficient matched game or player data for research holdouts')
    report = {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'research_only': True, 'production_changed': False,
              'description': 'Ridge scoring research baseline, not live-card forecasts; season holdouts train on earlier seasons only.',
              'features': {'coach': 'last-known head coach prior-game neutral and trailing pass rates',
                           'defense': 'prior five team games yards allowed per run and pass play'},
              'limitations': ['Head-coach proxy, not coordinator identity or verified pregame coaching announcement',
                              'Baselines are retrospective research models, not saved live-card forecasts',
                              'Only games with all feature groups are compared',
                              'Observed results do not establish causal or future improvement'],
              'coverage': coverage, 'game_results': results, 'player_results': player_results}
    out = Path('data/coach-matchup-research.json')
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
