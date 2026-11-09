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
 def test_winner_ats_and_total_picks_are_graded_on_official_lines(self):
  game="2026_09_A_B"
  rows=[{**row(game,"live",3),"stat_key":"game_margin_home"},
        {**row(game,"ml_ridge",-1),"stat_key":"game_margin_home"},
        {**row(game,"live",40),"stat_key":"game_total"},
        {**row(game,"ml_ridge",44),"stat_key":"game_total"}]
  actuals={(game,"game_margin_home"):4,(game,"game_total"):45}
  lines={game:{"dk_home_spread":-2.5,"dk_total":43.5}}
  out=paired(rows,actuals,lines)
  graded={(x["market"],x["model"]):x for x in out["pick_results"]}
  self.assertEqual((graded[("winner","live")]["hits"],graded[("winner","ml_ridge")]["misses"]),(1,1))
  self.assertEqual((graded[("ats","live")]["hits"],graded[("ats","ml_ridge")]["misses"]),(1,1))
  self.assertEqual((graded[("over_under","live")]["misses"],graded[("over_under","ml_ridge")]["hits"]),(1,1))
 def test_missing_lines_do_not_create_ats_or_total_grades(self):
  game="2026_09_A_B"
  rows=[{**row(game,"live",3),"stat_key":"game_margin_home"},
        {**row(game,"ml_ridge",-1),"stat_key":"game_margin_home"},
        {**row(game,"live",40),"stat_key":"game_total"},
        {**row(game,"ml_ridge",44),"stat_key":"game_total"}]
  out=paired(rows,{(game,"game_margin_home"):4,(game,"game_total"):45})
  self.assertEqual({x["market"] for x in out["pick_results"]},{"winner"})
if __name__=="__main__":unittest.main()
