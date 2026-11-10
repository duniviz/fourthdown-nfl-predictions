"""Research-only walk-forward evaluation of returning QB workload estimates.

Input: nflverse weekly player-stats CSV for consecutive seasons, including
player_id, position, season, week, attempts, passing_yards, season_type.
Rows for the target game are used for grading only, never for estimation.
The target sample uses >=20 actual attempts as a retrospective full-game proxy;
it is not evidence that a player was confirmed to start before kickoff.
"""
import argparse
import csv
import json
from collections import defaultdict
from math import sqrt


def candidate(history):
    """Blend recent meaningful appearances with current-season usage."""
    meaningful = [r for r in history if float(r['attempts'] or 0) >= 20][-5:]
    if len(meaningful) < 3:
        return None
    attempts = sum(float(r['attempts']) for r in meaningful)
    yards = sum(float(r['passing_yards'] or 0) for r in meaningful)
    if not attempts:
        return None
    volume = attempts / len(meaningful)
    # A conservative league prior limits overreaction to a small efficiency sample.
    rate = (yards + 100 * 6.6) / (attempts + 100)
    return volume * rate


def evaluate(rows):
    by_player = defaultdict(list)
    for r in rows:
        try:
            if r.get('position') != 'QB' or str(r.get('season_type', 'REG')).upper() not in ('REG', '2'):
                continue
            int(r['season']); int(r['week']); float(r['attempts'] or 0); float(r['passing_yards'] or 0)
            if not r.get('player_id'):
                continue
            by_player[r['player_id']].append(r)
        except (ValueError, TypeError, KeyError):
            continue
    pairs = []
    for records in by_player.values():
        records.sort(key=lambda r: (int(r['season']), int(r['week'])))
        for i, target in enumerate(records):
            season, week = int(target['season']), int(target['week'])
            history = [r for r in records[:i] if (int(r['season']), int(r['week'])) < (season, week)]
            current = [r for r in history if int(r['season']) == season]
            # Evaluate limited-current-history QBs conditional on a substantial
            # eventual workload. This selection is retrospective and optimistic.
            if not 1 <= len(current) <= 2 or float(target['attempts'] or 0) < 20:
                continue
            prediction = candidate(history)
            if prediction is None:
                continue
            baseline = sum(float(r['passing_yards'] or 0) for r in current) / len(current)
            actual = float(target['passing_yards'] or 0)
            pairs.append((baseline, prediction, actual))
    if not pairs:
        return {'sample_size': 0, 'note': 'No eligible matched games; no validation conclusion.'}
    def scores(index):
        errors = [p[index] - p[2] for p in pairs]
        return {'mae': round(sum(abs(e) for e in errors)/len(errors), 2),
                'rmse': round(sqrt(sum(e*e for e in errors)/len(errors)), 2)}
    return {'sample_size': len(pairs), 'baseline_recent_yards': scores(0),
            'candidate': scores(1), 'note': 'Retrospective >=20-attempt filter; baseline is recent average, not the live model. Research only.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_path')
    args = parser.parse_args()
    with open(args.csv_path, newline='', encoding='utf-8-sig') as f:
        print(json.dumps(evaluate(list(csv.DictReader(f))), indent=2))

if __name__ == '__main__':
    main()
