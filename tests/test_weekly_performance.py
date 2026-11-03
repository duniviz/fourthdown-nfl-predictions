import sys,unittest
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from track_weekly_performance import snapshot,grade,metrics
NOW=datetime(2026,10,27,tzinfo=timezone.utc)
class TrackingTests(unittest.TestCase):
 def setUp(self):
  self.schedule=[{"season":"2026","week":"9","game_type":"REG","game_id":"g1","home_team":"A","away_team":"B","gameday":"2026-11-01","gametime":"13:00","home_score":"","away_score":""}]
  self.games={"season":2026,"week":9,"games":[{"game_id":"g1","home":"A","away":"B","projected_margin_home":3,"projected_total":44}]}
  self.players={"season":2026,"week":9,"projections":[{"game_id":"g1","player_id":"p1","market":"passing_yards","projected_yards":250}]}
 def test_no_backfill_after_kickoff(self):
  with self.assertRaises(ValueError):snapshot(self.games,self.players,self.schedule,datetime(2026,11,2,tzinfo=timezone.utc))
 def test_no_grade_before_final(self):
  record=snapshot(self.games,self.players,self.schedule,NOW)
  result=grade(record,self.schedule,[],NOW)
  self.assertEqual(result["completed_games"],0)
  self.assertIsNone(result["player_metrics"]["passing_yards"]["mae"])
 def test_grade_observed(self):
  record=snapshot(self.games,self.players,self.schedule,NOW)
  self.schedule[0].update(home_score="27",away_score="20")
  stats=[{"season":"2026","week":"9","player_id":"p1","passing_yards":"260","rushing_yards":"0","receiving_yards":"0"}]
  result=grade(record,self.schedule,stats,datetime(2026,11,3,tzinfo=timezone.utc))
  self.assertEqual(result["player_metrics"]["passing_yards"]["mae"],10)
  self.assertEqual(result["game_metrics"]["total"]["mae"],3)
  self.assertEqual(result["game_metrics"]["home_margin"]["mae"],4)
 def test_metrics_empty(self):self.assertIsNone(metrics([])["rmse"])
if __name__=="__main__":unittest.main()
