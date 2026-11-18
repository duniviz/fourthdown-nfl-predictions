import unittest
from tools.ml_challengers import evaluate, walkforward_split
class MLChallengerTests(unittest.TestCase):
 def test_requires_multiple_seasons(self):
  self.assertEqual(evaluate([{"season":2025,"market":"passing_yards"}])["status"],"insufficient_seasons")
 def test_current_season_only_earlier_weeks_enter_training(self):
  rows=[{"season":2025,"week":18},{"season":2026,"week":2},{"season":2026,"week":3},{"season":2026,"week":4}]
  train,test=walkforward_split(rows,2026,3)
  self.assertEqual([(r["season"],r["week"]) for r in train],[(2025,18),(2026,2)])
  self.assertEqual([(r["season"],r["week"]) for r in test],[(2026,3)])
 def test_xgboost_is_scored_on_same_player_holdout(self):
  rows=[{"season":season,"week":week,"market":"passing_yards","features":[float(i),float(i),float(week)],"actual":float(i+2),"baseline":float(i)} for season in (2024,2025) for week in range(1,4) for i in range(40)]
  result=evaluate(rows)["markets"]["passing_yards"]
  self.assertEqual(result["holdout"],120)
  self.assertIn("xgboost",result["challengers"])
  self.assertEqual(result["current_season_training_weeks"],[1,2])
 def test_small_samples_do_not_train(self):
  rows=[{"season":season,"week":1,"market":"passing_yards","features":[10.,10.,1.],"actual":10.,"baseline":10.} for season in (2024,2025)]
  self.assertEqual(evaluate(rows)["markets"]["passing_yards"]["status"],"insufficient_samples")
if __name__=="__main__":unittest.main()
