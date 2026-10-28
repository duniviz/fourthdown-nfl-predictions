import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from calibrate_player_residuals import percentile,build
class CalibrationTests(unittest.TestCase):
 def test_percentile(self):
  self.assertEqual(percentile([0,10],.5),5)
 def test_insufficient_history_not_calibrated(self):
  rows=[{"season":"2026","week":str(w),"season_type":"REG","player_id":"P","player_name":"Player","recent_team":"GB","passing_yards":"100","rushing_yards":"0","receiving_yards":"0","attempts":"20","carries":"0","targets":"0"} for w in range(1,6)]
  result=build(rows,2026,5)
  self.assertNotEqual(result["markets"]["passing_yards"]["status"],"validated_research_distribution")
if __name__=="__main__":unittest.main()
