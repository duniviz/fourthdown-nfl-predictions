import unittest
from model.engine import TeamRating, GameInput, expected_scores, simulate

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.game = GameInput(away=TeamRating("A"), home=TeamRating("H"))

    def test_home_advantage(self):
        away, home = expected_scores(self.game)
        self.assertEqual((away, home), (22.0, 23.5))

    def test_reproducible(self):
        a = simulate(self.game, n=500, seed=10, spread_home=-2.5, total_line=44.5)
        b = simulate(self.game, n=500, seed=10, spread_home=-2.5, total_line=44.5)
        self.assertEqual(a, b)
        self.assertAlmostEqual(a["home_win_probability"] + a["away_win_probability"] + a["tie_probability"], 1, places=3)
        self.assertAlmostEqual(a["home_cover_probability"] + a["away_cover_probability"] + a["spread_push_probability"], 1, places=3)
        self.assertAlmostEqual(a["over_probability"] + a["under_probability"] + a["total_push_probability"], 1, places=3)

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            simulate(self.game, n=0)
        with self.assertRaises(ValueError):
            simulate(self.game, score_sd=1, shared_sd=2)

if __name__ == "__main__":
    unittest.main()
