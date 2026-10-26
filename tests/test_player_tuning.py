import unittest

from live.player_research import clamp, game_script_multiplier


class PlayerTuningTests(unittest.TestCase):
    def test_clamp_bounds_values(self):
        self.assertEqual(clamp(4, -1, 1), 1)
        self.assertEqual(clamp(-4, -1, 1), -1)
        self.assertEqual(clamp(0.5, -1, 1), 0.5)

    def test_game_script_is_capped_and_directional(self):
        self.assertGreater(game_script_multiplier("rushing_yards", 20), 1.0)
        self.assertLess(game_script_multiplier("rushing_yards", -20), 1.0)
        self.assertLess(game_script_multiplier("passing_yards", 20), 1.0)
        self.assertGreater(game_script_multiplier("receiving_yards", -20), 1.0)
        self.assertEqual(game_script_multiplier("rushing_yards", 1000), 1.06)


if __name__ == "__main__":
    unittest.main()
