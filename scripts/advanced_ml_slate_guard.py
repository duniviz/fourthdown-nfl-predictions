"""Coordinate research feature refreshes with the published player slate."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def read(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError, TypeError):
        return {}


def stamp(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (AttributeError, TypeError, ValueError):
        return None


def matched(slate, runtime, features):
    try:
        target = (int(slate['season']), int(slate['week']))
        return (target == (int(runtime['target_season']), int(runtime['target_week']))
                == (int(features['target_season']), int(features['target_week']))
                and runtime['family'] == features['family'] == 'free-nfl-advanced-ridge-v1'
                and runtime['research_only'] is True and features['research_only'] is True
                and runtime['generated_at_utc'] == features['generated_at_utc']
                and bool(runtime['models']) and bool(features['players'])
                and stamp(runtime['generated_at_utc']) is not None)
    except (KeyError, TypeError, ValueError):
        return False


def should_refresh(slate, players, runtime, features):
    try:
        target = (int(slate['season']), int(slate['week']))
        player_target = (int(players['season']), int(players['week']))
        if target != player_target or not slate.get('games') or not players.get('players'):
            return False
        return not matched(slate, runtime, features)
    except (KeyError, TypeError, ValueError):
        return False


def should_publish(slate, players, runtime, features, now):
    if not matched(slate, runtime, features):
        return False
    try:
        if (int(slate['season']), int(slate['week'])) != (int(players['season']), int(players['week'])):
            return False
        feature_time = stamp(runtime['generated_at_utc'])
        player_time = stamp(players['generated_at_utc'])
        return bool(feature_time and player_time and player_time < feature_time <= now)
    except (KeyError, TypeError, ValueError):
        return False


def main():
    files = [read('data/live-v2.json'), read('data/player-research.json'),
             read('data/player-advanced-ml-runtime.json'),
             read('data/player-advanced-ml-features.json')]
    if sys.argv[1:] == ['needs-refresh']:
        result = should_refresh(*files)
    elif sys.argv[1:] == ['ready-to-publish']:
        result = should_publish(*files, datetime.now(timezone.utc))
    else:
        raise SystemExit('Expected needs-refresh or ready-to-publish')
    raise SystemExit(0 if result else 1)


if __name__ == '__main__':
    main()
