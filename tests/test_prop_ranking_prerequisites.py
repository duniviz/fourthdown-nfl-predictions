import unittest
from datetime import datetime,timezone
from tools.rank_prop_research import evaluate
class RankingTests(unittest.TestCase):
 def test_unverified_blocks_even_with_large_gap(self):
  now=datetime.now(timezone.utc)
  r=evaluate({"comparisons":[{"match_status":"matched","recommendation_eligible":False,"availability_status":"unverified","dk_line":40,"projected_yards":90,"last_update":now.isoformat()}]},now)
  self.assertEqual(r["counts"]["eligible_for_further_validation"],0)
  self.assertIsNone(r["comparisons"][0]["confidence_score"])
 def test_stale_quote_blocks(self):
  now=datetime.now(timezone.utc)
  r=evaluate({"comparisons":[{"match_status":"matched","recommendation_eligible":True,"availability_status":"active","dk_line":40,"projected_yards":55,"last_update":"2020-01-01T00:00:00Z"}]},now)
  self.assertIn("quote_not_fresh",r["comparisons"][0]["block_reasons"])
if __name__=="__main__":unittest.main()
