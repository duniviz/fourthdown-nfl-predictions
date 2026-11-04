import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"research"))
from grade_paired_game_models import paired

def row(game,model,projection,at="2026-11-01T15:00:00Z"):
 return {"game_id":game,"player_id":"GAME","stat_key":"game_total","model":model,
         "projection":projection,"kickoff_utc":"2026-11-01T18:00:00Z","predicted_at_utc":at}

class PairedGradingTests(unittest.TestCase):
 def test_identical_game_sample_for_each_challenger(self):
  rows=[row("2026_09_A_B","live",40),row("2026_09_A_B","ml_ridge",44),
        row("2026_09_C_D","live",55),row("2026_09_C_D","ml_random_forest",49)]
  actuals={("2026_09_A_B","game_total"):45,("2026_09_C_D","game_total"):50}
  out=paired(rows,actuals)
  models={x["challenger"]:x for x in out["comparisons"]}
  self.assertEqual(models["ml_ridge"]["matched_games"],1)
  self.assertEqual(models["ml_ridge"]["production_mae"],5)
  self.assertEqual(models["ml_random_forest"]["production_mae"],5)
  self.assertFalse(out["auto_promotion_enabled"])
 def test_post_kickoff_rejected(self):
  rows=[row("2026_09_A_B","live",40),row("2026_09_A_B","ml_ridge",44,"2026-11-01T19:00:00Z")]
  out=paired(rows,{("2026_09_A_B","game_total"):45})
  self.assertFalse(out["comparisons"])
  self.assertEqual(out["rejected"]["invalid_pregame_forecast"],1)
 def test_missing_incumbent_never_compared(self):
  out=paired([row("2026_09_A_B","ml_ridge",44)],{("2026_09_A_B","game_total"):45})
  self.assertFalse(out["comparisons"])
if __name__=="__main__":unittest.main()
