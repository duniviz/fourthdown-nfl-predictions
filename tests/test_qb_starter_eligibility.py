import unittest

from live.qb_starter_eligibility import verified_qb_starter


class VerifiedQbStarterTests(unittest.TestCase):
    def setUp(self):
        self.rows = {
            ("2026_10_LAC_BAL", "BAL", "QB"): [
                {"player": "Lamar Jackson", "status": "projected", "depth_rank": 2},
                {"player": "Jacoby Brissett", "status": "projected", "depth_rank": 1},
            ]
        }

    def test_only_projected_qb_one_is_eligible(self):
        row = verified_qb_starter(
            self.rows, "2026_10_LAC_BAL", "BAL", "Jacoby Brissett")
        self.assertEqual(row["depth_rank"], 1)
        self.assertIsNone(verified_qb_starter(
            self.rows, "2026_10_LAC_BAL", "BAL", "Lamar Jackson"))

    def test_official_confirmation_overrides_missing_depth_rank(self):
        rows = {("2026_10_LAC_BAL", "BAL", "QB"): [
            {"player": "Jacoby Brissett", "status": "confirmed"}
        ]}
        self.assertEqual(
            verified_qb_starter(rows, "2026_10_LAC_BAL", "BAL", "Jacoby Brissett")["status"],
            "confirmed")

    def test_wrong_game_or_team_does_not_match(self):
        self.assertIsNone(verified_qb_starter(
            self.rows, "2026_11_LAC_BAL", "BAL", "Jacoby Brissett"))
        self.assertIsNone(verified_qb_starter(
            self.rows, "2026_10_LAC_BAL", "LAC", "Jacoby Brissett"))

    def test_unknown_player_fails_closed(self):
        self.assertIsNone(verified_qb_starter(
            self.rows, "2026_10_LAC_BAL", "BAL", ""))


if __name__ == "__main__":
    unittest.main()
