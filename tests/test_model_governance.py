import unittest
from tools.model_governance import decisions
class GovernanceTests(unittest.TestCase):
 def test_promising_candidate_still_blocked_from_live(self):
  player={"markets":{"passing_yards":{"status":"evaluated","baseline_mae":60,"holdout":400,
   "challengers":{"ridge":{"mae":55},"random_forest":{"mae":58}}}}}
  r=decisions(player,{"status":"awaiting_frozen_weather_and_verified_outcomes"})
  self.assertTrue(r["decisions"]["passing_yards"]["research_candidate"])
  self.assertFalse(r["automatic_promotion_enabled"])
  self.assertFalse(r["live_weights_changed"])
  self.assertFalse(r["decisions"]["passing_yards"]["production_changed"])
 def test_tiny_improvement_retains_champion(self):
  player={"markets":{"rushing_yards":{"status":"evaluated","baseline_mae":24,"holdout":900,
   "challengers":{"ridge":{"mae":23.99}}}}}
  self.assertEqual(decisions(player,{})["decisions"]["rushing_yards"]["decision"],"retain_champion")
if __name__=="__main__":unittest.main()
