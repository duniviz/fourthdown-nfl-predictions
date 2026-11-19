"""Completed-game, player-level situational features from nflverse play-by-play."""
from collections import defaultdict
import math


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def load_completed_pbp(nfl, season, finals):
    import polars as pl
    columns = ['game_id', 'play_id', 'season', 'week', 'season_type', 'play_type',
               'passer_player_id', 'receiver_player_id', 'rusher_player_id',
               'yardline_100', 'air_yards', 'yards_gained']
    frame = nfl.load_pbp([season])
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError('Missing play-by-play columns: ' + ', '.join(sorted(missing)))
    frame = frame.select(columns).filter(
        pl.col('game_id').is_in(list(finals)) & (pl.col('season_type') == 'REG')
        & pl.col('play_id').is_not_null() & pl.col('play_type').is_in(['pass', 'run']))
    keys = ['game_id', 'play_id']
    return frame.filter(~pl.struct(keys).is_duplicated()).to_dicts()


def add_situational_features(series, rows):
    # A missing observation is never interpreted as a failed play.
    weekly = defaultdict(lambda: [[], [], []])
    for row in rows:
        try:
            season, week = int(row['season']), int(row['week'])
        except (KeyError, TypeError, ValueError):
            continue
        if week < 1 or row.get('season_type') != 'REG':
            continue
        zone = number(row.get('yardline_100'))
        air = number(row.get('air_yards'))
        yards = number(row.get('yards_gained'))
        zone_value = None if zone is None else float(zone <= 20)
        if row.get('play_type') == 'pass':
            values = [zone_value, None if air is None else float(air >= 20), air]
            players = [('passing_yards', row.get('passer_player_id')),
                       ('receiving_yards', row.get('receiver_player_id'))]
        elif row.get('play_type') == 'run':
            values = [zone_value, None if yards is None else float(yards >= 10),
                      None if yards is None else float(yards <= 0)]
            players = [('rushing_yards', row.get('rusher_player_id'))]
        else:
            continue
        for market, player in players:
            if not player:
                continue
            bucket = weekly[(market, str(player), season, week)]
            for i, value in enumerate(values):
                if value is not None:
                    bucket[i].append(value)
    for (market, player, season, week), values in weekly.items():
        if all(values):
            series[('situational_' + market, player)].append(
                ((season, week), [sum(v) / len(v) for v in values]))
    return len(rows)
