import unittest
from research.qb_starter_workload import candidate, evaluate


def row(season, week, attempts, yards):
    return {'player_id': 'qb', 'position': 'QB', 'season': season, 'week': week,
            'attempts': attempts, 'passing_yards': yards, 'season_type': 'REG'}


class StarterWorkloadResearchTests(unittest.TestCase):
    def test_requires_three_meaningful_games(self):
        self.assertIsNone(candidate([row(2025, 1, 30, 200), row(2025, 2, 5, 40)]))

    def test_target_outcome_does_not_change_projection(self):
        history = [row(2025, i, 30, 210) for i in (1, 2, 3)] + [row(2026, 1, 10, 50)]
        before = candidate(history)
        self.assertEqual(before, candidate(history))
        a = evaluate(history + [row(2026, 2, 25, 100)])
        b = evaluate(history + [row(2026, 2, 25, 300)])
        self.assertEqual(a['sample_size'], 1)
        self.assertEqual(b['sample_size'], 1)
        self.assertNotEqual(a['candidate']['mae'], b['candidate']['mae'])

    def test_no_eligible_games(self):
        self.assertEqual(evaluate([])['sample_size'], 0)

if __name__ == '__main__':
    unittest.main()
