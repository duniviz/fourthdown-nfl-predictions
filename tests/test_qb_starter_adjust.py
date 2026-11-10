import unittest

from live.qb_starter_adjust import estimate_starter_adjustment


class QbStarterAdjustmentTests(unittest.TestCase):
    def setUp(self):
        self.schedules = []
        self.stats = []
        for week in range(1, 4):
            self.schedules.extend([
                {"season": 2026, "week": week, "game_type": "REG",
                 "home_team": "MIN", "away_team": "GB",
                 "home_score": 20, "away_score": 17},
                {"season": 2026, "week": week, "game_type": "REG",
                 "home_team": "LV", "away_team": "KC",
                 "home_score": 24, "away_score": 20},
            ])
            self.stats.extend([
                {"season": 2026, "week": week, "team": "MIN", "position": "QB",
                 "player_display_name": "Kyler Murray", "attempts": 30,
                 "passing_yards": 180, "rushing_yards": 10,
                 "passing_tds": 1, "interceptions": 1},
                {"season": 2026, "week": week, "team": "LV", "position": "QB",
                 "player_display_name": "Kirk Cousins", "attempts": 30,
                 "passing_yards": 270, "rushing_yards": 0,
                 "passing_tds": 2, "interceptions": 0},
            ])

    def test_incoming_qb_changes_team_score_with_capped_low_confidence_delta(self):
        result = estimate_starter_adjustment(
            "MIN", {"player": "Kirk Cousins", "status": "projected"},
            self.stats, self.schedules, 4, 2026)
        self.assertEqual(result["status"], "experimental_incoming_qb_adjustment")
        self.assertEqual(result["confidence"], "low")
        self.assertGreater(result["points"], 0)
        self.assertLessEqual(abs(result["points"]), 2)

    def test_current_team_starter_is_not_counted_twice(self):
        result = estimate_starter_adjustment(
            "MIN", {"player": "Kyler Murray", "status": "confirmed"},
            self.stats, self.schedules, 4, 2026)
        self.assertEqual(result["status"], "starter_already_in_team_baseline")
        self.assertEqual(result["points"], 0)

    def test_missing_or_unconfirmed_starter_fails_closed(self):
        result = estimate_starter_adjustment(
            "MIN", None, self.stats, self.schedules, 4, 2026)
        self.assertEqual(result["status"], "starter_context_unavailable")
        result = estimate_starter_adjustment(
            "MIN", {"player": "Kirk Cousins", "status": "unconfirmed"},
            self.stats, self.schedules, 4, 2026)
        self.assertEqual(result["status"], "starter_status_unusable")
        self.assertEqual(result["points"], 0)

    def test_insufficient_history_does_not_guess(self):
        result = estimate_starter_adjustment(
            "MIN", {"player": "Rookie", "status": "projected"},
            self.stats, self.schedules, 4, 2026)
        self.assertEqual(result["status"], "incoming_starter_insufficient_prior_games")
        self.assertEqual(result["points"], 0)


if __name__ == "__main__":
    unittest.main()
