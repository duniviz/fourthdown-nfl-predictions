import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from live.pregame_cycle import fresh_dk_totals, validate_due_locks


class PregameFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.kickoff = datetime(2026, 11, 27, 1, 20, tzinfo=timezone.utc)
        self.game = {
            "game_id": "2026_12_KC_BUF",
            "away": "KC",
            "home": "BUF",
            "kickoff_utc": self.kickoff.isoformat(),
        }

    def quote(self, observed):
        return {
            "bookmaker": "draftkings",
            "away": "KC",
            "home": "BUF",
            "commence_time": self.kickoff.isoformat(),
            "total": 44.5,
            "total_observed_at_utc": observed.isoformat(),
        }

    def test_draftkings_total_must_be_captured_within_hour_before_kickoff(self):
        now = self.kickoff - timedelta(minutes=10)
        with patch("live.pregame_cycle.read", return_value={"games": [self.quote(self.kickoff-timedelta(minutes=45))]}):
            self.assertTrue(fresh_dk_totals([self.game],[self.kickoff.isoformat()],now))
        with patch("live.pregame_cycle.read", return_value={"games": [self.quote(self.kickoff-timedelta(minutes=61))]}):
            self.assertFalse(fresh_dk_totals([self.game],[self.kickoff.isoformat()],now))
        with patch("live.pregame_cycle.read", return_value={"games": []}):
            self.assertFalse(fresh_dk_totals([self.game],[self.kickoff.isoformat()],now))

    def test_lock_requires_recent_forecast_and_saved_dk_total(self):
        now = self.kickoff - timedelta(minutes=20)
        lock = {
            **self.game,
            "lock_status": "last_available",
            "forecast_at_utc": (self.kickoff-timedelta(minutes=50)).isoformat(),
            "dk_at_utc": (self.kickoff-timedelta(minutes=45)).isoformat(),
            "dk_total": 44.5,
        }
        with patch("live.pregame_cycle.read", return_value={"records": [lock]}):
            validate_due_locks([self.game],now)
        stale = {**lock,"dk_at_utc":(self.kickoff-timedelta(minutes=61)).isoformat()}
        with patch("live.pregame_cycle.read", return_value={"records": [stale]}):
            with self.assertRaisesRegex(RuntimeError,"DK total fresh=False"):
                validate_due_locks([self.game],now)
        missing = {**lock,"dk_total":None}
        with patch("live.pregame_cycle.read", return_value={"records": [missing]}):
            with self.assertRaisesRegex(RuntimeError,"DK total fresh=False"):
                validate_due_locks([self.game],now)


if __name__ == "__main__":
    unittest.main()
