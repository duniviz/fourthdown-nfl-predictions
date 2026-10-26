import unittest
from backtest.rolling import build_rolling_predictions, summarize

class RollingTests(unittest.TestCase):
    def test_no_same_week_leakage(self):
        schedules = []
        team_games = []
        for week in range(1, 6):
            schedules.append(dict(season=2025, week=week, game_id=f"g{week}", home_team="H", away_team="A", home_score=20+week, away_score=14, game_type="REG"))
            for team in ("H", "A"):
                team_games.append(dict(season=2025, week=week, team=team, offense_epa=0.1, defense_epa=-0.1))
        a = build_rolling_predictions(schedules, team_games)
        self.assertEqual([r["week"] for r in a], [4, 5])
        # Changing week 4 stats must not affect week 4 prediction.
        for r in team_games:
            if r["week"] == 4 and r["team"] == "H": r["offense_epa"] = 1000
        b = build_rolling_predictions(schedules, team_games)
        self.assertEqual(a[0]["pred_margin"], b[0]["pred_margin"])
        self.assertNotEqual(a[1]["pred_margin"], b[1]["pred_margin"])
        self.assertEqual(summarize(a)["games"], 2)

if __name__ == "__main__":
    unittest.main()
