import unittest
from datetime import datetime, timedelta, timezone
from research.import_official_game_locks import merge

class OfficialLockBridgeTests(unittest.TestCase):
    def lock(self):
        kickoff = datetime(2026, 11, 8, 18, tzinfo=timezone.utc)
        cutoff = kickoff - timedelta(minutes=15)
        return {
            "game_id": "2026_09_X_Y", "lock_status": "official",
            "kickoff_utc": kickoff.isoformat(), "lock_cutoff_utc": cutoff.isoformat(),
            "forecast_at_utc": (cutoff-timedelta(minutes=5)).isoformat(),
            "dk_at_utc": (cutoff-timedelta(minutes=5)).isoformat(),
            "captured_at_utc": (cutoff-timedelta(minutes=4)).isoformat(),
            "projected_total": 44.5, "projected_margin_home": 3.0,
            "dk_total": 43.5, "dk_home_spread": -2.5,
        }

    def test_import_is_idempotent_and_preserves_incumbent(self):
        first, count, rejected = merge([self.lock()], [])
        self.assertEqual((count, rejected), (2, 0))
        second, count, rejected = merge([self.lock()], first)
        self.assertEqual((count, rejected), (0, 0))
        self.assertEqual(first, second)
        self.assertEqual({r["model"] for r in second}, {"live"})

    def test_post_cutoff_observation_is_rejected(self):
        lock = self.lock()
        lock["captured_at_utc"] = lock["kickoff_utc"]
        rows, added, rejected = merge([lock], [])
        self.assertEqual((rows, added, rejected), ([], 0, 1))

    def test_unofficial_lock_rejected(self):
        lock = self.lock()
        lock["lock_status"] = "pending"
        self.assertEqual(merge([lock], [])[1:], (0, 1))

if __name__ == "__main__":
    unittest.main()
