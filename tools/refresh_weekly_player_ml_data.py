#!/usr/bin/env python3
"""Rebuild research player backtests from completed games only.

A game's statistics are eligible only when the schedule has a completed final
score. live.backtest_players uses strictly earlier weeks to form each forecast.
This dataset is retrospective; it is not an archive of production forecasts.
"""
import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import nflreadpy as nfl
import live.backtest_players as backtester


class Rows:
    def __init__(self, rows): self.rows = rows
    def to_dicts(self): return self.rows


class CompletedGamesReader:
    def __init__(self, source): self.source = source
    def load_player_stats(self, seasons, summary_level='week'):
        schedules = self.source.load_schedules(seasons).to_dicts()
        finals = {str(g['game_id']) for g in schedules if g.get('game_type') == 'REG'
                  and g.get('home_score') is not None and g.get('away_score') is not None
                  and g.get('game_id')}
        stats = self.source.load_player_stats(seasons, summary_level=summary_level).to_dicts()
        if not finals:
            print(f'No completed games in {seasons}; excluding this season')
            return Rows([])
        filtered = [r for r in stats if str(r.get('game_id') or '') in finals]
        if stats and not filtered:
            raise ValueError(f'No player rows matched completed game IDs in {seasons}')
        print(f'{seasons}: {len(finals)} completed games, {len(filtered)} player rows')
        return Rows(filtered)


def build(start, end, output):
    previous = backtester.nfl
    try:
        backtester.nfl = CompletedGamesReader(nfl)
        rows = backtester.backtest(tuple(range(start, end+1)))
    finally:
        backtester.nfl = previous
    if not rows:
        raise ValueError('No historical player forecasts generated; refusing to replace training data')
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix('.tmp')
    with temp.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    temp.replace(output)
    print(f'Saved {len(rows)} retrospective rows; observed seasons: {sorted({r["season"] for r in rows})}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--start', type=int, default=2016)
    p.add_argument('--end', type=int, default=datetime.now(timezone.utc).year)
    p.add_argument('--output', type=Path, default=Path('data/weekly-player-ml-training.csv'))
    a = p.parse_args()
    if a.start < 2016 or a.end < a.start or a.end > datetime.now(timezone.utc).year:
        p.error('Invalid season range')
    build(a.start, a.end, a.output)

if __name__ == '__main__': main()
