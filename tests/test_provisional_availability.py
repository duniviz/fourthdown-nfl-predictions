import sys,unittest
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from rank_prop_research import evaluate
class ProvisionalTests(unittest.TestCase):
 def test_presumed_player_is_provisional_not_bet_eligible(self):
  now=datetime(2026,10,27,tzinfo=timezone.utc)
  row={"player_id":"P","market":"receiving_yards","availability_status":"presumed_available","provisional_research_eligible":True,"recommendation_eligible":False,"match_status":"matched","dk_line":55.5,"projected_yards":65,"last_update":now.isoformat()}
  x=evaluate({"comparisons":[row]},now=now)["comparisons"][0]
  self.assertEqual(x["provisional_research_status"],"provisional")
  self.assertEqual(x["ranking_status"],"blocked")
  self.assertIsNone(x["research_over_probability"])
 def test_inactive_cannot_be_provisional(self):
  now=datetime(2026,10,27,tzinfo=timezone.utc)
  row={"market":"receiving_yards","availability_status":"inactive","provisional_research_eligible":False,"recommendation_eligible":False,"match_status":"matched","dk_line":55.5,"projected_yards":65,"last_update":now.isoformat()}
  x=evaluate({"comparisons":[row]},now=now)["comparisons"][0]
  self.assertEqual(x["provisional_research_status"],"not_provisional")
if __name__=="__main__":unittest.main()
