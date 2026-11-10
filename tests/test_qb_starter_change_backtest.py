import unittest
from research.qb_starter_change_backtest import evaluate


def stat(season, week, player, yards=180, attempts=30, team='A'):
    return {'season': season, 'week': week, 'game_id': f'{season}_{week}', 'team': team,
            'position': 'QB', 'season_type': 'REG', 'player_id': player,
            'attempts': attempts, 'passing_yards': yards}


def game(week, qb):
    return {'season': 2025, 'week': week, 'game_id': f'2025_{week}', 'game_type': 'REG',
            'home_team': 'A', 'home_qb_id': qb, 'away_team': 'B', 'away_qb_id': ''}


class StarterChangeTests(unittest.TestCase):
    def test_starter_change_and_future_history(self):
        rows=[stat(2024, n, 'replacement') for n in (1, 2, 3)]
        rows += [stat(2025, 1, 'replacement', 20, 3), stat(2025, 2, 'replacement', 200, 30)]
        games=[game(1, 'first'), game(2, 'replacement')]
        a=evaluate(rows, games)
        b=evaluate(rows+[stat(2025, 3, 'replacement', 600, 60)], games)
        self.assertEqual(a, b)
        self.assertEqual(a['overall']['games'], 1)

    def test_same_starter_is_excluded(self):
        rows=[stat(2024, n, 'p') for n in (1, 2, 3)]+[stat(2025, n, 'p') for n in (1, 2)]
        self.assertEqual(evaluate(rows, [game(1, 'p'), game(2, 'p')])['overall']['games'], 0)

if __name__ == '__main__': unittest.main()
