import unittest
from tools.ml_challengers import evaluate
class MLChallengerTests(unittest.TestCase):
 def test_requires_multiple_seasons(self):
  self.assertEqual(evaluate([{"season":2025,"market":"passing_yards"}])["status"],"insufficient_seasons")
 def test_small_samples_do_not_train(self):
  rows=[{"season":season,"market":"passing_yards","features":[10.,10.,1.],"actual":10.,"baseline":10.} for season in (2024,2025)]
  self.assertEqual(evaluate(rows)["markets"]["passing_yards"]["status"],"insufficient_samples")
if __name__=="__main__":unittest.main()
