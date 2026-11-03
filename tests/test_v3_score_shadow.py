import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from v3_score_shadow import project

class V3ScoreShadowTests(unittest.TestCase):
    def setUp(self):
        self.v2 = {
            "season": 2026, "week": 9,
            "games": [{"game_id":"g1","season":2026,"week":9,"kickoff_utc":"2026-11-01T18:00:00+00:00",
                       "home":"H","away":"A","projected_total":44.0,"projected_margin_home":1.5}]
        }
        self.features = {"features":{
            "H":{"plays_per_game":68,"success_rate":0.50,"neutral_pass_proxy":0.60},
            "A":{"plays_per_game":58,"success_rate":0.40,"neutral_pass_proxy":0.50},
            "X":{"plays_per_game":62,"success_rate":0.45,"neutral_pass_proxy":0.55},
        }}

    def test_research_only_and_consistent_scores(self):
        result = project(self.v2, self.features, "2026-10-30T00:00:00+00:00")
        self.assertFalse(result["production_change_approved"])
        self.assertEqual(result["status"], "research_only_not_for_live_or_betting_use")
        game = result["games"][0]
        self.assertAlmostEqual(game["projected_total"], game["projected_home_score"] + game["projected_away_score"], places=1)
        self.assertAlmostEqual(game["projected_margin_home"], game["projected_home_score"] - game["projected_away_score"], places=1)
        self.assertLessEqual(abs(game["feature_adjustments"]["total_from_pace"]), 3)
        self.assertLessEqual(abs(game["feature_adjustments"]["margin_from_success_and_pass_proxy"]), 3)

    def test_missing_features_are_not_silently_invented(self):
        with self.assertRaises(ValueError):
            project(self.v2, {"features": {}}, "2026-10-30T00:00:00+00:00")

if __name__ == "__main__":
    unittest.main()
