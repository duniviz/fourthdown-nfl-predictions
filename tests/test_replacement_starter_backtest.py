import unittest
from research.replacement_starter_backtest import estimate, evaluate


def row(week, yards=70, attempts=30, position='QB'):
    return {'season': '2025', 'week': str(week), 'season_type': 'REG',
            'player_id': 'p', 'position': position, 'attempts': str(attempts),
            'passing_yards': str(yards), 'carries': '0', 'rushing_yards': '0',
            'targets': '0', 'receiving_yards': '0'}


class ReplacementResearchTests(unittest.TestCase):
    def test_all_four_positions_require_history(self):
        for market in ('passing_yards', 'rushing_yards', 'receiving_yards', 'te_receiving_yards'):
            self.assertIsNone(estimate([], market))

    def test_target_outcome_never_used_as_input(self):
        history = [row(1), row(2), row(3)]
        forecast = [{'season': '2025', 'week': '6', 'player_id': 'p',
                     'market': 'passing_yards', 'actual': '100', 'new': '90'}]
        a = evaluate(history + [row(6, 100)], forecast)
        b = evaluate(history + [row(6, 900)], forecast)
        self.assertEqual(a, b)
        self.assertEqual(a['results'][0]['games'], 1)

    def test_no_saved_comparator_is_not_a_pass(self):
        result = evaluate([row(1), row(2), row(3), row(6)], [])
        self.assertEqual(result['results'], [])
        self.assertEqual(result['status'], 'research_only')

if __name__ == '__main__':
    unittest.main()
