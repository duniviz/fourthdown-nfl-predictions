import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from backtest_player_yards_walkforward import evaluate
class BacktestTests(unittest.TestCase):
 def test_prior_week_only(self):
  rows=[]
  for week in range(1,6):
   rows.append({"season":"2026","week":str(week),"season_type":"REG","player_id":"P1","player_name":"Player One","recent_team":"GB","passing_yards":str(100*week),"rushing_yards":"0","receiving_yards":"0","attempts":"20","carries":"0","targets":"0"})
  result=evaluate(rows,2026,5)
  self.assertEqual(result["markets"]["passing_yards"]["samples"],2)
  self.assertGreater(result["markets"]["passing_yards"]["mae"],0)
  self.assertEqual(result["weeks"]["4"]["evaluated"],1)
if __name__=="__main__":unittest.main()
