import unittest
from datetime import datetime,timedelta,timezone
from live.pregame_capture_guard import due_refresh,due_lock,evening_key
from live.pregame_cycle import category_done,slate_done
from live.generate import VERIFIED_KICKOFF_OVERRIDES

class PregameScheduleTests(unittest.TestCase):
    def test_week_nine_flex_kickoff(self):
        self.assertEqual(VERIFIED_KICKOFF_OVERRIDES["2026_09_LV_SF"],"2026-11-08T16:25:00")
    def test_one_paid_refresh_per_slate(self):
        kickoff=datetime(2026,11,8,18,tzinfo=timezone.utc)
        games=[{"kickoff_utc":kickoff.isoformat()}]*2
        self.assertEqual(due_refresh(games,set(),kickoff-timedelta(minutes=30)),[kickoff])
        self.assertEqual(due_refresh(games,{kickoff.isoformat()},kickoff-timedelta(minutes=30)),[])
        self.assertEqual(due_refresh(games,set(),kickoff-timedelta(minutes=19)),[kickoff])
        self.assertEqual(due_refresh(games,set(),kickoff-timedelta(minutes=15)),[kickoff])
        self.assertEqual(due_refresh(games,set(),kickoff-timedelta(minutes=14)),[])
    def test_evening_no_game_central_daylight_and_standard(self):
        for hour in (0,1):
            now=datetime(2026,11,7,hour,tzinfo=timezone.utc) if hour==1 else datetime(2026,7,8,0,tzinfo=timezone.utc)
            self.assertIsNotNone(evening_key([],set(),now))
            key=evening_key([],set(),now)
            self.assertIsNone(evening_key([],{key},now))
            self.assertIsNone(evening_key([{"kickoff_utc":now.isoformat()}],set(),now))
    def test_evening_outside_window(self):
        now=datetime(2026,11,7,2,tzinfo=timezone.utc)
        self.assertIsNone(evening_key([],set(),now))
    def test_independent_t15_lock(self):
        kickoff=datetime(2026,11,8,18,tzinfo=timezone.utc)
        games=[{"kickoff_utc":kickoff.isoformat()}]
        self.assertFalse(due_lock(games,kickoff-timedelta(minutes=16)))
        self.assertTrue(due_lock(games,kickoff-timedelta(minutes=15)))
        self.assertFalse(due_lock(games,kickoff))
    def test_scoring_and_player_refresh_are_one_slate_checkpoint(self):
        key="2026-11-08T18:00:00+00:00"
        state={"refreshes":{key:{"game_odds":{"status":"request_completed"}}},"slates":[]}
        self.assertTrue(category_done(state,key,"game_odds"))
        self.assertFalse(category_done(state,key,"player_props"))
        self.assertFalse(slate_done(state,key))
        state["refreshes"][key]["player_props"]={"status":"request_completed"}
        self.assertTrue(slate_done(state,key))
    def test_failed_category_does_not_count_as_refreshed(self):
        key="2026-11-08T18:00:00+00:00"
        state={"refreshes":{key:{"game_odds":{"status":"failed"},
                                  "player_props":{"status":"request_completed"}}}}
        self.assertFalse(slate_done(state,key))
if __name__=="__main__":unittest.main()
