"""Deterministic, offline operations watchdog tests."""
import unittest
from datetime import datetime, timedelta, timezone
from scripts.operations_watchdog import inspect

NOW = datetime(2026, 11, 15, 18, 0, tzinfo=timezone.utc)


def iso(moment):
    return moment.isoformat()


def fixtures():
    kickoff = NOW - timedelta(minutes=30)
    game = {"game_id": "2026_10_TEST", "kickoff_utc": iso(kickoff)}
    slate = {"generated_at_utc": iso(NOW - timedelta(hours=2)), "games": [game]}
    locks = [{"game_id": game["game_id"], "captured_at_utc": iso(kickoff - timedelta(minutes=15)),
              "forecast_at_utc": iso(kickoff - timedelta(hours=2))}]
    snaps = [{"game_id": game["game_id"], "kickoff": iso(kickoff),
              "captured_at": iso(kickoff - timedelta(minutes=20)),
              "saved_at_utc": iso(kickoff - timedelta(minutes=10))}]
    return slate, locks, snaps


class WatchdogTests(unittest.TestCase):
    def test_valid_started_game(self):
        self.assertEqual(inspect(*fixtures(), NOW), [])

    def test_missing_scoring_lock(self):
        slate, _, snaps = fixtures()
        self.assertTrue(any("game forecast" in x for x in inspect(slate, [], snaps, NOW)))

    def test_missing_player_capture(self):
        slate, locks, _ = fixtures()
        self.assertTrue(any("player projections" in x for x in inspect(slate, locks, [], NOW)))

    def test_stale_active_slate(self):
        slate, locks, snaps = fixtures()
        slate["generated_at_utc"] = iso(NOW - timedelta(hours=40))
        self.assertTrue(any("36 hours" in x for x in inspect(slate, locks, snaps, NOW)))

    def test_offseason_stale_slate_is_ignored(self):
        slate, locks, snaps = fixtures()
        slate["games"][0]["kickoff_utc"] = iso(NOW - timedelta(days=60))
        slate["generated_at_utc"] = iso(NOW - timedelta(days=60))
        self.assertEqual(inspect(slate, locks, snaps, NOW), [])

    def test_bad_kickoff_timestamp(self):
        slate, locks, snaps = fixtures()
        slate["games"][0]["kickoff_utc"] = "invalid"
        self.assertTrue(any("invalid kickoff" in x for x in inspect(slate, locks, snaps, NOW)))


if __name__ == "__main__":
    unittest.main()
