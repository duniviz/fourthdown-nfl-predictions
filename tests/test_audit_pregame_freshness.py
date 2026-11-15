"""Offline tests for strict, read-only pregame freshness monitoring."""
import unittest
from datetime import datetime, timedelta, timezone
from scripts.audit_pregame_freshness import audit

NOW = datetime(2026, 11, 15, 18, tzinfo=timezone.utc)


def iso(value):
    return value.isoformat()


def fixtures():
    kickoff = NOW + timedelta(hours=3)
    slate = {"generated_at_utc": iso(NOW - timedelta(hours=2)), "games": [
        {"game_id": "g1", "home": "DET", "away": "NE", "kickoff_utc": iso(kickoff)}]}
    odds = {"games": [{"home": "DET", "away": "NE", "commence_time": iso(kickoff),
                       "home_spread_last_verified_at_utc": iso(NOW - timedelta(hours=1)),
                       "total_last_verified_at_utc": iso(NOW - timedelta(hours=1))}]}
    starters = {"starters": [{"game_id": "g1", "team": "DET", "position": "QB",
                             "status": "projected", "observed_at_utc": iso(NOW)}]}
    return slate, odds, starters


class AuditTest(unittest.TestCase):
    def test_healthy(self):
        self.assertEqual(audit(*fixtures(), NOW), ([], []))

    def test_missing_line_is_warning_not_fabricated(self):
        slate, odds, starters = fixtures()
        errors, warnings = audit(slate, {"games": []}, starters, NOW)
        self.assertFalse(errors)
        self.assertTrue(any("matching DraftKings" in x for x in warnings))

    def test_stale_odds_warning(self):
        slate, odds, starters = fixtures()
        odds["games"][0]["total_last_verified_at_utc"] = iso(NOW - timedelta(hours=15))
        odds["games"][0]["home_spread_last_verified_at_utc"] = iso(NOW - timedelta(hours=15))
        self.assertTrue(any("12 hours" in w for w in audit(slate, odds, starters, NOW)[1]))

    def test_stale_forecast_warning(self):
        slate, odds, starters = fixtures()
        slate["generated_at_utc"] = iso(NOW - timedelta(hours=20))
        self.assertTrue(any("18 hours" in w for w in audit(slate, odds, starters, NOW)[1]))

    def test_future_forecast_is_error(self):
        slate, odds, starters = fixtures()
        slate["generated_at_utc"] = iso(NOW + timedelta(hours=1))
        self.assertTrue(audit(slate, odds, starters, NOW)[0])

    def test_unverified_qb_role_warning(self):
        slate, odds, starters = fixtures()
        starters["starters"][0]["observed_at_utc"] = iso(NOW - timedelta(days=5))
        self.assertTrue(any("QB projected" in w for w in audit(slate, odds, starters, NOW)[1]))

    def test_duplicate_confirmed_qbs_is_error(self):
        slate, odds, starters = fixtures()
        starters["starters"][0]["status"] = "confirmed"
        starters["starters"].append(dict(starters["starters"][0]))
        self.assertTrue(any("multiple confirmed" in e for e in audit(slate, odds, starters, NOW)[0]))

    def test_old_games_not_reflagged(self):
        slate, odds, starters = fixtures()
        slate["games"][0]["kickoff_utc"] = iso(NOW - timedelta(days=8))
        self.assertEqual(audit(slate, odds, starters, NOW), ([], []))


if __name__ == "__main__":
    unittest.main()
