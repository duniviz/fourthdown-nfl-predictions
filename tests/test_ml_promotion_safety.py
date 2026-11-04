"""Behavioral tests for fail-closed model promotion."""
import unittest
from tools.ml_auto_promotion import decide

MARKET="passing_yards"
FLAGS=("independent_chronological_replay_passed","multiweek_stability_passed",
       "cross_market_regression_passed","rollback_test_passed")

def inputs():
    report={"markets":{MARKET:{"status":"evaluated","holdout":450,
        "baseline_mae":50.0,"challengers":{"candidate":{"mae":46.0}},
        "production_validation":{flag:True for flag in FLAGS}}}}
    registry={"markets":{MARKET:{"champion":"baseline","version":"v1"}},
              "deployable":{MARKET:{"candidate":True}},
              "artifacts":{MARKET:{"candidate":"verified-v2"}}}
    return report,registry

class PromotionSafetyTests(unittest.TestCase):
    def test_complete_evidence_still_requires_separate_deployment(self):
        report,registry=inputs()
        decision=decide(report,registry)
        self.assertFalse(decision["automatic_promotion_enabled"])
        self.assertEqual(decision["promotions"],0)
        self.assertEqual(decision["markets"][MARKET]["action"],"keep")
        self.assertEqual(decision["markets"][MARKET]["champion"],"baseline")
        self.assertEqual(decision["markets"][MARKET]["research_candidate"],"candidate")
    def test_missing_each_gate_blocks(self):
        for flag in FLAGS:
            with self.subTest(flag=flag):
                report,registry=inputs()
                del report["markets"][MARKET]["production_validation"][flag]
                decision=decide(report,registry)["markets"][MARKET]
                self.assertEqual(decision["action"],"keep")
                self.assertNotIn("research_candidate",decision)
    def test_insufficient_holdout_blocks(self):
        report,registry=inputs()
        report["markets"][MARKET]["holdout"]=299
        self.assertEqual(decide(report,registry)["markets"][MARKET]["action"],"keep")
    def test_weak_challenger_blocks(self):
        report,registry=inputs()
        report["markets"][MARKET]["challengers"]["candidate"]["mae"]=49.0
        self.assertNotIn("research_candidate",decide(report,registry)["markets"][MARKET])
    def test_undeployable_candidate_blocks(self):
        report,registry=inputs()
        registry["deployable"][MARKET]["candidate"]=False
        self.assertEqual(decide(report,registry)["markets"][MARKET]["action"],"keep")
    def test_registry_not_mutated(self):
        report,registry=inputs()
        before=repr(registry)
        decide(report,registry)
        self.assertEqual(repr(registry),before)

if __name__=="__main__":
    unittest.main()
