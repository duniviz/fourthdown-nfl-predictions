import unittest

from tools.game_market_challengers import build_examples, evaluate


class GameMarketChallengerTests(unittest.TestCase):
    def setUp(self):
        self.schedule = [
            {
                "game_id": "2024_01_A_B", "season": 2024, "week": 1,
                "game_type": "REG", "home_team": "A", "away_team": "B",
                "home_score": 24, "away_score": 20, "spread_line": 3,
                "total_line": 44,
            },
            {
                "game_id": "2024_01_A_C", "season": 2024, "week": 1,
                "game_type": "REG", "home_team": "A", "away_team": "C",
                "home_score": 10, "away_score": 10, "spread_line": 0,
                "total_line": 20,
            },
            {
                "game_id": "2024_02_A_D", "season": 2024, "week": 2,
                "game_type": "REG", "home_team": "A", "away_team": "D",
                "home_score": 30, "away_score": 20, "spread_line": 4,
                "total_line": 45,
            },
        ]

    def test_lines_create_correct_cover_total_and_push_targets(self):
        rows = build_examples(self.schedule)
        first, second = rows[0], rows[1]
        self.assertEqual(first["ats_residual"], 1)
        self.assertEqual(first["home_cover"], 1)
        self.assertEqual(first["ou_residual"], 0)
        self.assertTrue(first["total_push"])
        self.assertEqual(second["ats_residual"], 0)
        self.assertTrue(second["spread_push"])
        self.assertEqual(second["ou_residual"], 0)
        self.assertTrue(second["total_push"])

    def test_features_use_prior_weeks_and_withhold_same_week_games(self):
        rows = build_examples(self.schedule)
        # Both week-one games see no week-one results for team A.
        self.assertEqual(rows[0]["features"][1], 0)
        self.assertEqual(rows[1]["features"][1], 0)
        # Week two sees both completed week-one games for A.
        self.assertEqual(rows[2]["features"][1], 2)
        self.assertEqual(rows[2]["features"][2], 17)

    def test_insufficient_seasons_are_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(build_examples(self.schedule))


if __name__ == "__main__":
    unittest.main()
