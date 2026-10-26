import unittest
from backtest.v2 import build_v2_predictions
from backtest.compare import compare

class V2Tests(unittest.TestCase):
    def data(self):
        schedules, team_games = [], []
        for week in range(1, 7):
            schedules.append(dict(season=2025, week=week, game_id=f"2025_{week}",
                                  home_team="H", away_team="A", home_score=24,
                                  away_score=17, game_type="REG"))
            team_games += [
                dict(season=2025, week=week, team="H", offense_epa=0.1, defense_epa=-0.02),
                dict(season=2025, week=week, team="A", offense_epa=-0.04, defense_epa=0.05)]
        return schedules, team_games

    def test_week_is_frozen(self):
        schedules, rows = self.data()
        a = build_v2_predictions(schedules, rows)
        self.assertEqual([r["week"] for r in a], [4, 5, 6])
        for row in rows:
            if row["week"] == 4 and row["team"] == "H":
                row["offense_epa"] = 5.0
        b = build_v2_predictions(schedules, rows)
        self.assertEqual(a[0]["pred_margin"], b[0]["pred_margin"])
        self.assertNotEqual(a[1]["pred_margin"], b[1]["pred_margin"])

    def test_matched_comparison(self):
        schedules, rows = self.data()
        result = compare(schedules, rows)
        self.assertEqual(result["matched_games"], 3)
        self.assertEqual(result["held_out_2025"]["v2"]["games"], 3)

if __name__ == "__main__":
    unittest.main()
