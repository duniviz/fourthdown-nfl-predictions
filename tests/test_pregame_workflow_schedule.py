"""Ensure existing scheduled capture has sufficient T-15 attempts and no relaxed cutoff."""
import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from live.pregame_capture_guard import due_lock, due_refresh

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/capture-game-pregame.yml"


class CaptureTimingTests(unittest.TestCase):
    def test_existing_workflow_checks_every_ten_minutes(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        crons = re.findall(r"cron:\s*'([0-9,]+) \* \* \* \*'", source)
        self.assertEqual(len(crons), 1)
        minutes = sorted({int(n) for n in crons[0].split(",")})
        self.assertEqual(minutes, [2, 12, 22, 32, 42, 52])
        gaps = [b-a for a, b in zip(minutes, minutes[1:])] + [minutes[0]+60-minutes[-1]]
        self.assertLessEqual(max(gaps), 10)

    def test_lock_only_after_t15_and_before_kickoff(self):
        kickoff = datetime(2026, 11, 16, 1, 20, tzinfo=timezone.utc)
        games = [{"kickoff_utc": kickoff.isoformat()}]
        self.assertFalse(due_lock(games, kickoff-timedelta(minutes=16)))
        self.assertTrue(due_lock(games, kickoff-timedelta(minutes=15)))
        self.assertTrue(due_lock(games, kickoff-timedelta(minutes=3)))
        self.assertFalse(due_lock(games, kickoff))
        self.assertFalse(due_lock(games, kickoff+timedelta(minutes=1)))

    def test_existing_t30_paid_refresh_window_unchanged(self):
        kickoff = datetime(2026, 11, 16, 1, 20, tzinfo=timezone.utc)
        games = [{"kickoff_utc": kickoff.isoformat()}]
        self.assertEqual(due_refresh(games, set(), kickoff-timedelta(minutes=30)), [kickoff])
        self.assertEqual(due_refresh(games, set(), kickoff-timedelta(minutes=15)), [kickoff])
        self.assertEqual(due_refresh(games, set(), kickoff-timedelta(minutes=14)), [])


if __name__ == "__main__":
    unittest.main()
