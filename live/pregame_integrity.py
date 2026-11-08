"""Check recently started games for persisted pregame forecasts and odds coverage."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from live.game_pregame_observations import dt

DATA = Path('data')

def inspect(games, locks, snapshots, now):
    locks_by_game = {str(row.get('game_id')): row for row in locks}
    issues = []
    coverage = []
    for game in games:
        kickoff = dt(game.get('kickoff_utc'))
        if not kickoff or not kickoff <= now < kickoff + timedelta(hours=3):
            continue
        game_id = str(game.get('game_id'))
        lock = locks_by_game.get(game_id, {})
        captured = dt(lock.get('captured_at_utc'))
        forecast = dt(lock.get('forecast_at_utc'))
        if not captured or not forecast or not forecast <= captured < kickoff:
            issues.append(f'{game_id}: no saved pregame scoring forecast')
        rows = [r for r in snapshots if str(r.get('game_id')) == game_id
                and dt(r.get('kickoff')) == kickoff and dt(r.get('captured_at'))
                and dt(r.get('saved_at_utc'))
                and dt(r['captured_at']) <= dt(r['saved_at_utc']) < kickoff]
        if not rows:
            issues.append(f'{game_id}: no saved pregame player projections')
        valid_lines = sum(1 for row in rows if row.get('dk_line') is not None
                          and dt(row.get('dk_captured_at'))
                          and dt(row['dk_captured_at']) <= dt(row['saved_at_utc']))
        coverage.append((game_id, len(rows), valid_lines))
    return issues, coverage

def main():
    def read(name, key):
        path = DATA / name
        return json.loads(path.read_text()).get(key, []) if path.exists() else []
    issues, coverage = inspect(read('live-v2.json','games'),
                               read('game-official-pregame-locks.json','records'),
                               read('pregame-snapshots.json','records'), datetime.now(timezone.utc))
    for game_id, total, lines in coverage:
        print(f'{game_id}: {total} pregame player projections, {lines} with verified DK lines')
        if total and lines == 0:
            print(f'::warning::{game_id}: no verified DK player lines were captured')
    if issues:
        raise SystemExit('\n'.join(issues))
    print('Recently started games have saved pregame predictions')

if __name__ == '__main__':
    main()
