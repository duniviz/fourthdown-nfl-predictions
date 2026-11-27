"""Dynamic game-day refresh schedule and pregame capture safeguards."""
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from live.pregame_capture_guard import due_lock, due_refresh, lock_wait_seconds


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / ".github/workflows/capture-game-pregame.yml"
FORECAST = ROOT / ".github/workflows/publish-v2.yml"
CT = timezone.utc


class CaptureTimingTests(unittest.TestCase):
    def test_dynamic_schedules_cover_every_day_without_hard_coded_kickoffs(self):
        capture = CAPTURE.read_text(encoding="utf-8")
        forecast = FORECAST.read_text(encoding="utf-8")
        self.assertIn("cron: '8,38 * * * *'", capture)
        self.assertIn("cron: '8,38 * * * *'", forecast)
        self.assertNotIn("cron: '*/5 * * * *'", capture)
        self.assertNotIn("cron: '*/5 * * * *'", forecast)
        self.assertIn("scripts.pregame_window_wait", capture)
        self.assertIn("scripts.pregame_window_wait", forecast)
        self.assertNotIn("timezone:", capture)
        self.assertNotIn("timezone:", forecast)
        self.assertNotIn("Thu Nov 26", capture)
        self.assertNotIn("Sunday preset game-day refresh", capture)

    def test_writer_runs_only_when_a_window_is_due(self):
        source = CAPTURE.read_text(encoding="utf-8")
        self.assertIn("python -m scripts.pregame_window_wait --role capture", source)
        self.assertIn("timeout-minutes: 45", source)
        self.assertIn("group: pregame-pipeline", source)
        preflight = source.split("capture:", 1)[0]
        self.assertIn("pregame-capture-arm", preflight)
        self.assertNotIn("pregame-pipeline", preflight)
        self.assertIn("cancel-in-progress: false", source)

    def test_lock_only_inside_t30_window_before_kickoff(self):
        kickoff = datetime(2026, 11, 16, 1, 20, tzinfo=CT)
        games = [{"kickoff_utc": kickoff.isoformat()}]
        self.assertFalse(due_lock(games, kickoff-timedelta(minutes=31)))
        self.assertTrue(due_lock(games, kickoff-timedelta(minutes=30)))
        self.assertTrue(due_lock(games, kickoff-timedelta(minutes=3)))
        self.assertFalse(due_lock(games, kickoff))
        self.assertFalse(due_lock(games, kickoff+timedelta(minutes=1)))

    def test_wait_targets_t30(self):
        kickoff=datetime(2026,11,16,1,20,tzinfo=CT)
        games=[{"kickoff_utc":kickoff.isoformat()}]
        self.assertEqual(lock_wait_seconds(games,kickoff-timedelta(minutes=40)),600)
        self.assertEqual(lock_wait_seconds(games,kickoff-timedelta(minutes=30)),0)

    def test_paid_refresh_is_once_per_kickoff_and_retries_until_t5(self):
        kickoff=datetime(2026,11,16,1,20,tzinfo=CT)
        games=[{"kickoff_utc":kickoff.isoformat()}]*2
        self.assertEqual(due_refresh(games,set(),kickoff-timedelta(minutes=45)),[kickoff])
        self.assertEqual(due_refresh(games,set(),kickoff-timedelta(minutes=30)),[kickoff])
        self.assertEqual(due_refresh(games,set(),kickoff-timedelta(minutes=10)),[kickoff])
        self.assertEqual(due_refresh(games,{kickoff.isoformat()},kickoff-timedelta(minutes=30)),[])
        self.assertEqual(due_refresh(games,set(),kickoff-timedelta(minutes=4)),[])


if __name__ == "__main__":
    unittest.main()
