"""Walk-forward, paired scoring ablation; never publishes a production model."""
import gc
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


def main():
    years = list(range(2019, datetime.now(timezone.utc).year + 1))
    schedules = nfl.load_schedules(years).to_dicts()
    rows, coverage = [], {}
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
            coverage[str(year)] = {'plays': len(plays), 'baseline_games': len(base), 'matched_games': len(matched)}
            del frame, plays, base, ctx, matched
            gc.collect()
        except Exception as exc:
            coverage[str(year)] = {'error': f'{type(exc).__name__}: {exc}'}
            print('Unavailable season:', year, type(exc).__name__, str(exc), flush=True)
    results = evaluate(rows)
    if not results:
        raise RuntimeError('Insufficient matched data for the research holdouts')
    report = {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'research_only': True, 'production_changed': False,
              'description': 'Ridge scoring research baseline, not live-card forecasts; season holdouts train on earlier seasons only.',
              'features': {'coach': 'last-known head coach prior-game neutral and trailing pass rates',
                           'defense': 'prior five team games yards allowed per run and pass play'},
              'limitations': ['Head-coach proxy, not coordinator identity or verified pregame coaching announcement',
                              'Baseline is a research model, not the live scoring model',
                              'Only games with all feature groups are compared',
                              'Observed results do not establish causal or future improvement'],
              'coverage': coverage, 'results': results}
    out = Path('data/coach-matchup-research.json')
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
