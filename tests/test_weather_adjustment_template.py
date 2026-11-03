import unittest
from tools.weather_adjustment_template import scenario,adjusted_projection
class TemplateTests(unittest.TestCase):
    def test_calm_no_adjustment(self):
        w=scenario(3,70)
        self.assertEqual(adjusted_projection("game_total",45,w),45)
    def test_windy_changes_games_and_props(self):
        w=scenario(22,25)
        self.assertEqual(adjusted_projection("game_total",45,w),42)
        self.assertLess(adjusted_projection("passing_yards",250,w),250)
        self.assertGreater(adjusted_projection("rush_attempts",20,w),20)
    def test_combined_weather_capped(self):
        w=scenario(30,10,True)
        self.assertEqual(w.total_points_delta,-7)
        self.assertGreaterEqual(w.pass_yards_pct,-.18)
        self.assertLessEqual(w.rush_attempts_pct,.08)
    def test_closed_roof_no_effect(self):
        self.assertEqual(adjusted_projection("passing_yards",250,scenario(30,0,True,"closed")),250)
    def test_missing_forecast_fail_closed(self):
        self.assertIsNone(scenario(None,25))
        self.assertIsNone(adjusted_projection("game_total",45,None))
    def test_rush_yards_accounts_for_efficiency(self):
        w=scenario(30,20,True)
        self.assertAlmostEqual(adjusted_projection("rushing_yards",100,w),100*1.08*.94)
if __name__=="__main__":unittest.main()
