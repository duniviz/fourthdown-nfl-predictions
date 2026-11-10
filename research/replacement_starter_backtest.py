"""Research-only comparison for players returning after a multiweek absence.

This is a proxy cohort, not verified pregame starter data. All candidate inputs
precede the target week; saved retrospective backtest predictions supply the
comparison. The result must not be used for automatic model promotion.
"""
import argparse
import csv
import json
import math
from collections import defaultdict

MARKETS = {'passing_yards': ('QB', 'attempts', 20, 6.6),
           'rushing_yards': ('RB', 'carries', 8, 4.2),
           'receiving_yards': ('WR', 'targets', 4, 7.0),
           'te_receiving_yards': ('TE', 'targets', 4, 7.0)}


def estimate(history, market):
    position, volume, threshold, prior = MARKETS[market]
    rows = [r for r in history if r.get('position') == position and float(r.get(volume) or 0) >= threshold][-5:]
    if len(rows) < 3:
        return None
    stat = 'receiving_yards' if market == 'te_receiving_yards' else market
    total_volume = sum(float(r[volume]) for r in rows)
    total_yards = sum(float(r.get(stat) or 0) for r in rows)
    prior_volume = 100 if position == 'QB' else 25
    rate = (total_yards + prior_volume * prior) / (total_volume + prior_volume)
    return max(0, total_volume / len(rows) * rate)


def evaluate(rows, forecasts):
    groups = defaultdict(list)
    for r in rows:
        if r.get('player_id') and r.get('season_type') == 'REG':
            groups[r['player_id']].append(r)
    lookup = {(str(r['season']), str(r['week']), r['player_id'], r['market']): r for r in forecasts}
    results = defaultdict(list)
    for pid, records in groups.items():
        records.sort(key=lambda r: (int(r['season']), int(r['week'])))
        for i, target in enumerate(records):
            season, week = int(target['season']), int(target['week'])
            history = [r for r in records[:i] if (int(r['season']), int(r['week'])) < (season, week)]
            current = [r for r in history if int(r['season']) == season]
            # This proxy is determined before the target week, without selecting
            # on the target game's observed opportunities or outcome.
            if not current or week - int(current[-1]['week']) < 3:
                continue
            for market, (position, _, _, _) in MARKETS.items():
                if target.get('position') != position:
                    continue
                stat = 'receiving_yards' if market == 'te_receiving_yards' else market
                saved = lookup.get((str(season), str(week), pid, stat))
                pred = estimate(history, market)
                if not saved or pred is None:
                    continue
                try:
                    actual = float(saved['actual']); baseline = float(saved['new'])
                    if not all(math.isfinite(v) for v in (actual, baseline, pred)):
                        continue
                except (ValueError, TypeError, KeyError):
                    continue
                results[(season, market)].append((baseline-actual, pred-actual))
    out = []
    for (season, market), errors in sorted(results.items()):
        metrics = lambda i: {'mae': round(sum(abs(e[i]) for e in errors)/len(errors), 2),
                             'rmse': round(math.sqrt(sum(e[i]**2 for e in errors)/len(errors)), 2)}
        out.append({'season': season, 'market': market, 'games': len(errors),
                    'saved_research_baseline': metrics(0), 'candidate': metrics(1)})
    return {'status': 'research_only', 'results': out,
            'limitations': ['Absence is a proxy, not verified replacement starter status.',
                'Historical comparison uses saved research forecasts, not production locks.',
                'Only players appearing in the saved backtest are included; this introduces selection bias.',
                'Same-week outcomes are excluded from candidate inputs.',
                'No automatic promotion or production projection changes.']}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('stats_csv'); p.add_argument('forecasts_csv'); p.add_argument('--output')
    a = p.parse_args()
    with open(a.stats_csv, newline='') as f: rows = list(csv.DictReader(f))
    with open(a.forecasts_csv, newline='') as f: forecasts = list(csv.DictReader(f))
    report = json.dumps(evaluate(rows, forecasts), indent=2) + '\n'
    if a.output:
        with open(a.output, 'w') as f: f.write(report)
    print(report)

if __name__ == '__main__':
    main()
