import unittest
from datetime import datetime,timedelta,timezone
from live.pregame_capture_guard import due_refresh,due_lock
from live.generate import VERIFIED_KICKOFF_OVERRIDES

class PregameScheduleTests(unittest.TestCase):
    def test_week_nine_flex_kickoff(self):
        self.assertEqual(VERIFIED_KICKOFF_OVERRIDES["2026_09_LV_SF"],"2026-11-08T16:25:00")
    def test_one_paid_refresh_per_slate(self):
        kickoff=datetime(2026,11,8,18,tzinfo=timezone.utc)
        games=[{"kickoff_utc":kickoff.isoformat()}]*2
        self.assertEqual(due_refresh(games,set(),kickoff-timedelta(minutes=30)),[kickoff])
        self.assertEqual(due_refresh(games,{kickoff.isoformat()},kickoff-timedelta(minutes=30)),[])
        self.assertEqual(due_refresh(games,set(),kickoff-timedelta(minutes=19)),[])
    def test_independent_t15_lock(self):
        kickoff=datetime(2026,11,8,18,tzinfo=timezone.utc)
        games=[{"kickoff_utc":kickoff.isoformat()}]
        self.assertFalse(due_lock(games,kickoff-timedelta(minutes=16)))
        self.assertTrue(due_lock(games,kickoff-timedelta(minutes=15)))
        self.assertFalse(due_lock(games,kickoff))
if __name__=="__main__":unittest.main()
