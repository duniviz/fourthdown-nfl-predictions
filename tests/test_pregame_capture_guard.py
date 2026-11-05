import unittest
from datetime import datetime,timedelta,timezone
from live.pregame_capture_guard import due
from live.generate import VERIFIED_KICKOFF_OVERRIDES

class PregameScheduleTests(unittest.TestCase):
    def test_week_nine_flex_kickoff(self):
        self.assertEqual(VERIFIED_KICKOFF_OVERRIDES["2026_09_LV_SF"],"2026-11-08T16:25:00")
    def test_capture_window_and_after_kickoff_lock(self):
        now=datetime(2026,11,8,20,tzinfo=timezone.utc)
        def game(minutes):
            return {"kickoff_utc":(now+timedelta(minutes=minutes)).isoformat()}
        self.assertTrue(due([game(150)],now))
        self.assertTrue(due([game(30)],now))
        self.assertTrue(due([game(-40)],now))
        self.assertFalse(due([game(151)],now))
        self.assertFalse(due([game(-46)],now))
        self.assertFalse(due([{"kickoff_utc":"bad"}],now))

if __name__=="__main__":
    unittest.main()
