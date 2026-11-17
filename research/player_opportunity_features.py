"""Completed-game weekly opportunity and opponent efficiency features.

Raw completed-game rows are indexed by observed week. Callers must use
strictly earlier weeks when producing either training or inference features.
"""
from collections import defaultdict
import math


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def add_weekly_features(series, rows, completed_games):
    eligible = []
    for row in rows:
        try:
            year, week = int(row['season']), int(row['week'])
            if (str(row.get('game_id') or '') not in completed_games or
                    row.get('season_type', 'REG') != 'REG' or week < 1 or
                    not row.get('player_id') or not row.get('team') or not row.get('opponent_team')):
                continue
            eligible.append((year, week, row))
        except (KeyError, TypeError, ValueError):
            continue

    counts = defaultdict(int)
    for _, _, row in eligible:
        counts[(str(row['game_id']), str(row['player_id']))] += 1
    eligible = [(year, week, row) for year, week, row in eligible
                if counts[(str(row['game_id']), str(row['player_id']))] == 1]

    carries = defaultdict(float)
    for year, week, row in eligible:
        carries[(year, week, row['team'])] += max(0.0, number(row.get('carries')) or 0.0)

    opponents = defaultdict(lambda: defaultdict(float))
    for year, week, row in eligible:
        key = (year, week)
        player = str(row['player_id'])
        targets = max(0.0, number(row.get('targets')) or 0.0)
        attempts = max(0.0, number(row.get('carries')) or 0.0)
        if targets:
            air = number(row.get('receiving_air_yards'))
            values = [number(row.get('target_share')), number(row.get('air_yards_share')),
                      air / targets if air is not None else None]
            if any(v is not None for v in values):
                series[('workload_receiving_yards', player)].append((key, values))
        if attempts:
            total = carries[(year, week, row['team'])]
            epa = number(row.get('rushing_epa'))
            values = [attempts / total if total else None,
                      number(row.get('target_share')), epa / attempts if epa is not None else None]
            series[('workload_rushing_yards', player)].append((key, values))

        d = opponents[(year, week, str(row['opponent_team']))]
        for prefix, volume, yards, epa, explosive in (
            ('pass', 'attempts', 'passing_yards', 'passing_epa', 'passing_20'),
            ('rush', 'carries', 'rushing_yards', 'rushing_epa', 'rushing_10'),
            ('rec', 'targets', 'receiving_yards', 'receiving_epa', 'receiving_20'),
        ):
            n = max(0.0, number(row.get(volume)) or 0.0)
            d[prefix + '_volume'] += n
            for label, field in (('yards', yards), ('epa', epa), ('explosive', explosive)):
                value = number(row.get(field))
                if value is not None:
                    d[prefix + '_' + label] += value
                    d[prefix + '_' + label + '_seen'] += 1

    for (year, week, defense), data in opponents.items():
        for market, prefix in (('passing_yards', 'pass'), ('rushing_yards', 'rush'),
                               ('receiving_yards', 'rec')):
            volume = data[prefix + '_volume']
            if not volume:
                continue
            values = [data[prefix + '_' + field] / volume
                      if data[prefix + '_' + field + '_seen'] else None
                      for field in ('yards', 'epa', 'explosive')]
            if any(value is not None for value in values):
                series[('matchup_' + market, defense)].append(((year, week), values))
    return len(eligible)
