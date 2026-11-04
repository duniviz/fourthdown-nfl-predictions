import csv,importlib.util,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("pir",ROOT/"research"/"player_impact_research.py")
pir=importlib.util.module_from_spec(spec);spec.loader.exec_module(pir)
class PlayerImpactTests(unittest.TestCase):
 def test_chronological_season_holdout(self):
  games=[]
  for season in (2023,2024,2025):
   for week in range(1,19):
    games.append(dict(season=season,week=week,home_team="BAL",away_team="JAX",home_score=20+week%4,away_score=17+week%3))
  r=pir.evaluate(games)
  self.assertEqual(r["seasons"]["2024"]["test_n"],15)
  self.assertEqual(r["seasons"]["2025"]["train_n"],30)
  self.assertFalse(r["production_modified"])
  self.assertEqual(r["verified_pregame_injury_games"],0)
 def test_no_baseline_for_short_history(self):
  r=pir.evaluate([dict(season=2023,week=1,home_team="BAL",away_team="JAX",home_score=20,away_score=17)])
  self.assertEqual(r["eligible_baseline_games"],0)
  self.assertIsNone(r["seasons"]["2024"]["player_impact"])
if __name__=="__main__":unittest.main()
