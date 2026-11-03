import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from publish_prop_desk_research import build
class DeskTests(unittest.TestCase):
 def test_no_inactive_and_no_invented_probabilities(self):
  rank={"season":2026,"week":8,"comparisons":[{"player_id":"1","availability_status":"presumed_available","provisional_research_status":"provisional","market":"receiving_yards","research_over_probability":None},{"player_id":"2","availability_status":"inactive","market":"rushing_yards"}]}
  cal={"markets":{"receiving_yards":{"status":"validated_research_distribution","holdout_samples":63}}}
  result=build(rank,cal)
  self.assertEqual(len(result["comparisons"]),1)
  self.assertIsNone(result["comparisons"][0]["research_over_probability"])
  self.assertEqual(result["market_validation"]["receiving_yards"]["holdout_samples"],63)
if __name__=="__main__":unittest.main()
