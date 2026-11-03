import unittest
import polars as pl
from tools.game_ml_challengers import rows_from_schedules,evaluate
class GameMLTests(unittest.TestCase):
 def test_no_same_week_or_future_leakage(self):
  rows=[
   dict(season=2024,week=1,home_team="A",away_team="B",home_score=40,away_score=0,game_type="REG"),
   dict(season=2024,week=1,home_team="A",away_team="C",home_score=5,away_score=5,game_type="REG"),
   dict(season=2024,week=2,home_team="A",away_team="B",home_score=10,away_score=10,game_type="REG")]
  got=rows_from_schedules(pl.DataFrame(rows))
  self.assertEqual(got[0]["features"][1],0)
  self.assertEqual(got[1]["features"][1],0)
  self.assertEqual(got[2]["features"][1],2)
 def test_insufficient_seasons_rejected(self):
  with self.assertRaises(ValueError):evaluate([{"season":2024}])
if __name__=="__main__":unittest.main()
