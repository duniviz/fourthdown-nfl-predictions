"""Replay QB starter changes with prior-week data; research only.

Schedule starter identities are retrospective outcomes, not proof of pregame
availability. The comparator is the live model's project_yards component,
not a reconstruction of full published production projections.
"""
import argparse
import csv
import json
import math
from collections import defaultdict
from live.player_research import project_yards
from research.qb_starter_workload import candidate


def evaluate(stats, schedules):
    by_player = defaultdict(list)
    by_game = {}
    for r in stats:
        if r.get('season_type') != 'REG' or r.get('position') != 'QB' or not r.get('player_id'):
            continue
        by_player[r['player_id']].append(r)
        by_game[(str(r.get('game_id')), str(r['player_id']))] = r
    for records in by_player.values():
        records.sort(key=lambda r: (int(r['season']), int(r['week'])))
    games = sorted((g for g in schedules if g.get('game_type') == 'REG'),
                   key=lambda g: (int(g['season']), int(g['week']), str(g.get('game_id'))))
    previous = {}
    result = defaultdict(list)
    for game in games:
        season, week = int(game['season']), int(game['week'])
        for side in ('home', 'away'):
            team, qb = str(game.get(side+'_team') or ''), str(game.get(side+'_qb_id') or '')
            if not team or not qb:
                continue
            key = (season, team)
            old = previous.get(key)
            previous[key] = qb
            if not old or old == qb:
                continue
            target = by_game.get((str(game['game_id']), qb))
            if not target:
                continue
            history = [r for r in by_player[qb] if (int(r['season']), int(r['week'])) < (season, week)]
            # Reproduce the current-season/team scope of the live component.
            current = [r for r in history if int(r['season']) == season and r.get('team') == team]
            if not current:
                continue
            proposed = candidate(history)
            if proposed is None:
                continue
            baseline = project_yards(current, 'passing_yards', 'attempts')[0]
            actual = float(target.get('passing_yards') or 0)
            result[season].append((baseline-actual, proposed-actual))
    def summary(errors):
        if not errors:
            return {'games': 0}
        def score(i):
            return {'mae': round(sum(abs(e[i]) for e in errors)/len(errors), 2),
                    'rmse': round(math.sqrt(sum(e[i]**2 for e in errors)/len(errors)), 2)}
        return {'games': len(errors), 'current_yardage_component': score(0), 'candidate': score(1)}
    return {'status': 'research_only', 'by_season': {str(y): summary(e) for y,e in sorted(result.items())},
            'overall': summary([e for group in result.values() for e in group]),
            'limitations': ['Schedule starter identities are known retrospectively, not verified before kickoff.',
                'Comparator is the live yardage component only, not a full production replay.',
                'Requires prior current-team playing time and three historical 20-attempt games; excludes other replacements.',
                'Only outcomes from earlier weeks are inputs; no automatic promotion.']}


def main():
    p=argparse.ArgumentParser(); p.add_argument('stats'); p.add_argument('schedule'); p.add_argument('--output')
    a=p.parse_args()
    with open(a.stats, newline='') as f: stats=list(csv.DictReader(f))
    with open(a.schedule, newline='') as f: schedule=list(csv.DictReader(f))
    report=json.dumps(evaluate(stats, schedule),indent=2)+'\n'
    if a.output:
        with open(a.output,'w') as f: f.write(report)
    print(report)

if __name__ == '__main__': main()
