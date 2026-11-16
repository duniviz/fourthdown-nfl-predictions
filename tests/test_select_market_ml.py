import unittest
from research.select_market_ml import choose_player, choose_games, select

def market(scores,coverage=None):
 return {"holdout_rows":200,"holdout_weeks":8,"source_coverage":coverage or {"ngs":120,"snap":135,"pfr":0},
  "models":{k:{"status":"evaluated","samples":200,"baseline_mae":70,
                "challenger_mae":v,"improvement_pct":round((70-v)/70*100,2)}
            for k,v in scores.items()}}

class MarketSelectionTests(unittest.TestCase):
 def test_passing_prefers_simple_configuration(self):
  self.assertEqual(choose_player("passing_yards",market({"baseline_features":63.9,"ngs":64.2,"combined":64.1}))["research_winner"],"baseline_features")
 def test_rush_and_receiving_can_choose_combined(self):
  self.assertEqual(choose_player("rushing_yards",market({"baseline_features":23.4,"ngs":23.3,"combined":23.2}))["research_winner"],"combined")
 def test_missing_pfr_cannot_be_selected(self):
  self.assertEqual(choose_player("receiving_yards",market({"baseline_features":24.5,"pfr_advanced":1}))["research_winner"],"baseline_features")
 def test_too_few_holdout_weeks_is_ineligible(self):
  d=market({"ngs":20});d["holdout_weeks"]=2
  self.assertIsNone(choose_player("passing_yards",d)["research_winner"])
 def test_small_game_paired_sample_cannot_promote(self):
  d={"decisions":{"game_margin_home":{"active":False,"paired":12,"weeks":1,"pick_checks":{
    "winner":{"games":12,"baseline_hits":7,"candidate_hits":8},
    "ats":{"games":12,"baseline_hits":5,"candidate_hits":7}}},
    "game_total":{"active":False,"paired":12,"weeks":1,"pick_checks":{"ou":{"games":12,"baseline_hits":8,"candidate_hits":9}}}}}
  picks=choose_games(d)
  self.assertTrue(all(p["research_winner"]=="baseline" for p in picks.values()))
  self.assertTrue(all(p["evidence_status"]=="insufficient_paired_game_evidence" for p in picks.values()))
 def test_report_is_advisory_not_live(self):
  result=select({"markets":{"passing_yards":market({"ngs":21})}},{"decisions":{}})
  self.assertTrue(result["research_only"])
  self.assertFalse(result["production_changed"])
  self.assertFalse(result["player"]["passing_yards"]["card_model_changed"])
if __name__=="__main__":unittest.main()
