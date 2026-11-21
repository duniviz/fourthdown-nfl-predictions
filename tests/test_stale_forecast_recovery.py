import unittest
from datetime import datetime, timedelta, timezone

from scripts.stale_forecast_recovery import recovery_due


class ForecastRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 21, 14, tzinfo=timezone.utc)
        self.slate = {"generated_at_utc": (self.now - timedelta(hours=31)).isoformat(),
                      "games": [{"kickoff_utc": (self.now + timedelta(days=1)).isoformat()}]}

    def test_stale_forecast_recovers_but_fresh_does_not(self):
        self.assertTrue(recovery_due(self.slate, self.now))
        self.slate["generated_at_utc"] = (self.now - timedelta(hours=29)).isoformat()
        self.assertFalse(recovery_due(self.slate, self.now))

    def test_kickoff_safety(self):
        for offset in (timedelta(hours=-2), timedelta(hours=2)):
            self.slate["games"].append({"kickoff_utc": (self.now + offset).isoformat()})
            self.assertFalse(recovery_due(self.slate, self.now))
            self.slate["games"].pop()

    def test_invalid_inactive_and_future_data_fail_closed(self):
        self.slate["games"].append({"kickoff_utc": "invalid"})
        self.assertFalse(recovery_due(self.slate, self.now))
        self.slate["games"] = [{"kickoff_utc": (self.now + timedelta(days=8)).isoformat()}]
        self.assertFalse(recovery_due(self.slate, self.now))
        self.slate["games"] = [{"kickoff_utc": (self.now + timedelta(days=1)).isoformat()}]
        self.slate["generated_at_utc"] = (self.now + timedelta(hours=1)).isoformat()
        self.assertFalse(recovery_due(self.slate, self.now))


if __name__ == "__main__":
    unittest.main()
