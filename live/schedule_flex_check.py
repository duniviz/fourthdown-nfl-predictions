"""Wake the forecast when a fresh scoreboard proves a future kickoff moved."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from live.verified_scoreboard_kickoffs import scoreboard_kickoffs, stamp


def changed_games(live, feed, now):
    if not isinstance(live, dict) or not isinstance(live.get('games'), list):
        return []
    rows = []
    for g in live['games']:
        try:
            old = stamp(g.get('kickoff_utc'))
            if not old or old <= now:
                continue
            rows.append({'game_id': str(g['game_id']), 'season': int(g['season']),
                         'week': int(g['week']), 'game_type': 'REG',
                         'home_team': g['home'], 'away_team': g['away'],
                         'gameday': old.date().isoformat(), 'old_kickoff': old})
        except (KeyError, TypeError, ValueError):
            continue
    verified = scoreboard_kickoffs(rows, feed, now)
    result = []
    for row in rows:
        new = verified.get(row['game_id'])
        if new and new - now >= timedelta(minutes=15) and abs(new - row['old_kickoff']) > timedelta(minutes=1):
            result.append(row['game_id'])
    return result


def main():
    try:
        live = json.loads(Path('data/live-v2.json').read_text())
        feed = json.loads(Path('data/espn-scoreboard-backup.json').read_text())
        changed = changed_games(live, feed, datetime.now(timezone.utc))
    except (OSError, ValueError, TypeError, AttributeError):
        changed = []
    print('Future verified schedule changes:', ', '.join(changed) if changed else 'none')
    return 0 if changed else 1


if __name__ == '__main__':
    raise SystemExit(main())
