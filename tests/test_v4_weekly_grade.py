import unittest

from research.v4_weekly_grade import eligible_actual_rows


class V4WeeklyGradeTests(unittest.TestCase):
    def test_ignores_player_markets_without_v4_weights(self):
        rows = [
            {"season": 2026, "week": 10, "market": "attempts"},
            {"season": 2026, "week": 10, "market": "passing_yards"},
            {"season": 2025, "week": 10, "market": "rushing_yards"},
        ]
        supported = {"passing_yards", "rushing_yards", "receiving_yards"}
        self.assertEqual(
            eligible_actual_rows(rows, supported),
            [{"season": 2026, "week": 10, "market": "passing_yards"}],
        )


if __name__ == "__main__":
    unittest.main()
