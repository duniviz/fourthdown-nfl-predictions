"""Tests for accuracy evidence and fail-closed promotion report."""
import unittest
from scripts.audit_ml_evidence import evaluate, summary


def source():
    return {"week_tested": "2026_week_9", "frozen_forecasts_only": True,
            "post_kickoff_forecasts_excluded": True,
            "paired_challenger_comparisons": [
                {"market": "game_margin_home", "challenger": "mix", "matched_observations": 13,
                 "production_mae": 9.0, "challenger_mae": 8.0},
                {"market": "passing_yards", "challenger": "forest", "matched_observations": 92,
                 "production_mae": 35.0, "challenger_mae": 33.5}]}


class EvidenceTests(unittest.TestCase):
    def test_single_week_blocks_even_good_research_gain(self):
        report = evaluate(source(), {"coverage": {"incomplete_player_game_markets": 602}})
        self.assertFalse(report["production_promotion_allowed"])
        self.assertFalse(report["market_leaders"]["game_margin_home"]["promotion_eligible"])
        self.assertEqual(report["market_leaders"]["game_margin_home"]["matched_observations"], 13)
        self.assertTrue(report["coverage"]["coverage_incomplete"])

    def test_invalid_mae_not_ranked(self):
        s = source()
        s["paired_challenger_comparisons"].append({
            "market": "game_margin_home", "challenger": "cheat", "matched_observations": 999,
            "production_mae": 9.0, "challenger_mae": float("nan")})
        result = evaluate(s, {})
        self.assertEqual(result["invalid_comparisons"], 1)
        self.assertEqual(result["market_leaders"]["game_margin_home"]["challenger"], "mix")

    def test_missing_frozen_provenance_fails_closed(self):
        s = source()
        s["frozen_forecasts_only"] = False
        with self.assertRaises(ValueError):
            evaluate(s, {})

    def test_missing_week_fails_closed(self):
        s = source()
        s.pop("week_tested")
        with self.assertRaises(ValueError):
            evaluate(s, {})

    def test_even_300_samples_do_not_prove_three_weeks(self):
        s = source()
        s["paired_challenger_comparisons"][1]["matched_observations"] = 450
        result = evaluate(s, {})
        self.assertFalse(result["market_leaders"]["passing_yards"]["promotion_eligible"])
        self.assertIn("only one evaluated week documented",
                      result["market_leaders"]["passing_yards"]["blockers"])

    def test_summary_never_claims_deployment(self):
        report = evaluate(source(), {})
        self.assertIn("production promotion: **BLOCKED**", summary(report))


if __name__ == "__main__":
    unittest.main()
