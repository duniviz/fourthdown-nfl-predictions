import unittest
from datetime import datetime, timedelta, timezone

from live.prop_recommendations import recommendation, no_vig_probabilities


class PropRecommendationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 27, tzinfo=timezone.utc)
        self.quote = {"bookmaker": "draftkings", "last_update": self.now.isoformat(),
                      "over_price": -110, "under_price": -110}
        self.calibrated = {"sample_size": 80, "probability_calibrated": True}

    def test_removes_vig_from_two_sided_market(self):
        probabilities = no_vig_probabilities(-110, -110)
        self.assertAlmostEqual(probabilities["over"], .5)
        self.assertAlmostEqual(probabilities["under"], .5)

    def test_recommendation_needs_calibration_and_value(self):
        rec = recommendation(.60, self.quote, self.calibrated, now=self.now)
        self.assertEqual(rec["recommendation"], "OVER")
        self.assertEqual(rec["confidence"], "High")
        self.assertGreater(rec["ev"], 0)
        self.assertEqual(recommendation(.60, self.quote, {"sample_size": 10}, now=self.now)["recommendation"], "PASS")

    def test_stale_and_injury_uncertain_quotes_are_passes(self):
        stale = dict(self.quote, last_update=(self.now - timedelta(hours=4)).isoformat())
        self.assertEqual(recommendation(.60, stale, self.calibrated, now=self.now)["recommendation"], "PASS")
        self.assertEqual(recommendation(.60, self.quote, self.calibrated, True, self.now)["recommendation"], "PASS")


if __name__ == "__main__":
    unittest.main()
