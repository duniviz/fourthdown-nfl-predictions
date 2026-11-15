"""Regression tests for one existing paired grader (no parallel learning pipeline)."""
import unittest
from research.grade_all_markets_paired import grade


def row(game, model, projection, player="GAME", market="game_total", late=False):
    return {"game_id": game, "player_id": player, "stat_key": market, "model": model,
            "projection": projection, "kickoff_utc": "2026-11-15T18:00:00Z",
            "predicted_at_utc": "2026-11-15T19:00:00Z" if late else "2026-11-15T17:00:00Z"}


class MultiweekTests(unittest.TestCase):
    def test_exact_pairing_not_cross_model_coverage(self):
        a, b = "2026_09_A_B", "2026_10_C_D"
        forecasts = [row(a, "live", 40), row(a, "ridge", 44),
                     row(b, "live", 50), row(b, "forest", 49)]
        actuals = {(a, "GAME", "game_total"): 45, (b, "GAME", "game_total"): 52}
        scores = {x["challenger"]: x for x in grade(forecasts, actuals)["scores"]}
        self.assertEqual(scores["ridge"]["matched_observations"], 1)
        self.assertEqual(scores["ridge"]["live_mae"], 5)
        self.assertEqual(scores["forest"]["live_mae"], 2)
        self.assertEqual(scores["forest"]["independent_weeks"], 1)

    def test_third_duplicate_cannot_reenter(self):
        g = "2026_09_A_B"
        forecasts = [row(g, "live", 40), row(g, "ridge", 41),
                     row(g, "ridge", 42), row(g, "ridge", 43)]
        report = grade(forecasts, {(g, "GAME", "game_total"): 45})
        self.assertEqual(report["scores"], [])
        self.assertEqual(report["rejected"]["duplicate_model"], 2)

    def test_duplicate_live_disqualifies_all_candidates(self):
        g = "2026_09_A_B"
        forecasts = [row(g, "live", 40), row(g, "live", 41), row(g, "ridge", 44)]
        self.assertEqual(grade(forecasts, {(g, "GAME", "game_total"): 45})["scores"], [])

    def test_postkickoff_and_missing_live_excluded(self):
        g = "2026_09_A_B"
        forecasts = [row(g, "live", 40), row(g, "ridge", 43, late=True)]
        out = grade(forecasts, {(g, "GAME", "game_total"): 45})
        self.assertEqual(out["scores"], [])
        self.assertEqual(out["rejected"]["invalid_or_postkickoff"], 1)

    def test_multiweek_reports_research_stability_not_promotion(self):
        forecasts, actuals = [], {}
        for week in (8, 9, 10):
            for i in range(40):
                g = f"2026_{week:02d}_A{i}_B{i}"
                forecasts += [row(g, "live", 40), row(g, "ridge", 44)]
                actuals[(g, "GAME", "game_total")] = 45
        report = grade(forecasts, actuals)
        leader = report["scores"][0]
        self.assertEqual(leader["matched_observations"], 120)
        self.assertEqual(leader["independent_weeks"], 3)
        self.assertEqual(leader["winning_weeks"], 3)
        self.assertTrue(leader["research_thresholds_met"])
        self.assertFalse(leader["promotion_eligible"])
        self.assertFalse(report["auto_promotion_enabled"])
        self.assertEqual(len(leader["weekly_results"]), 3)

    def test_single_week_never_passes_research_gate(self):
        g = "2026_09_A_B"
        result = grade([row(g, "live", 40), row(g, "ridge", 44)],
                       {(g, "GAME", "game_total"): 45})
        self.assertFalse(result["scores"][0]["research_thresholds_met"])

    def test_no_synthetic_actuals(self):
        g = "2026_09_A_B"
        result = grade([row(g, "live", 40), row(g, "ridge", 44)], {})
        self.assertEqual(result["scores"], [])


if __name__ == "__main__":
    unittest.main()
