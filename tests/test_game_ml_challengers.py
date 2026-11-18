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
 def test_xgboost_scores_total_margin_and_winner_on_same_games(self):
  rows=[{"season":season,"week":i%18+1,"features":[float(i%10),float(i%7)],"total":float(35+i%20),"margin":float(i%21-10),"winner":int(i%21>10)} for season in (2023,2024,2025) for i in range(160)]
  result=evaluate(rows)
  self.assertEqual(result["holdout_games"],160)
  self.assertIn("xgboost",result["markets"]["total"]["challengers"])
  self.assertIn("winner_accuracy_excluding_ties",result["markets"]["margin"]["challengers"]["xgboost"])
  self.assertTrue(result["research_only"])
 def test_insufficient_seasons_rejected(self):
  with self.assertRaises(ValueError):evaluate([{"season":2024}])
if __name__=="__main__":unittest.main()
