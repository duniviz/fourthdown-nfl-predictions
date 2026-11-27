import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

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

    def test_den_pit_forecast_from_1216_ct_is_fresh_at_t30(self):
        central = ZoneInfo("America/Chicago")
        kickoff = datetime(2026, 11, 27, 14, 0, tzinfo=central)
        forecast_at = datetime(2026, 11, 27, 12, 16, tzinfo=central)
        now = kickoff - timedelta(minutes=30)
        self.assertEqual(
            kickoff.astimezone(timezone.utc),
            datetime(2026, 11, 27, 20, 0, tzinfo=timezone.utc),
        )
        game = {
            "game_id": "2026_12_DEN_PIT",
            "away": "DEN",
            "home": "PIT",
            "kickoff_utc": kickoff.isoformat(),
        }
        lock = {
            **game,
            "lock_status": "official",
            "forecast_at_utc": forecast_at.isoformat(),
            "dk_at_utc": (kickoff - timedelta(minutes=40)).isoformat(),
            "dk_total": 36.5,
        }
        with patch("live.pregame_cycle.read", return_value={"records": [lock]}):
            validate_due_locks([game], now)
        on_the_hour = {**lock, "forecast_at_utc": (kickoff - timedelta(hours=2)).isoformat()}
        with patch("live.pregame_cycle.read", return_value={"records": [on_the_hour]}):
            validate_due_locks([game], now)
        too_old = {**lock, "forecast_at_utc": (kickoff - timedelta(minutes=121)).isoformat()}
        with patch("live.pregame_cycle.read", return_value={"records": [too_old]}):
            with self.assertRaisesRegex(RuntimeError, "forecast fresh=False"):
                validate_due_locks([game], now)


if __name__ == "__main__":
    unittest.main()
