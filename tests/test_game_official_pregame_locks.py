import unittest
from datetime import datetime,timedelta,timezone
from live.game_official_pregame_locks import select, freeze

class OfficialGameLockTests(unittest.TestCase):
    def setUp(self):
        self.kickoff=datetime(2026,11,8,18,tzinfo=timezone.utc)
    def row(self,minutes,spread, captured_minutes=None):
        t=(self.kickoff-timedelta(minutes=minutes)).isoformat()
        capture=(self.kickoff-timedelta(minutes=captured_minutes if captured_minutes is not None else minutes)).isoformat()
        return {"game_id":"g","kickoff_utc":self.kickoff.isoformat(),
                "forecast_at_utc":t,"dk_at_utc":t,"captured_at_utc":capture,
                "projected_margin_home":2,"projected_total":44,
                "dk_home_spread":spread,"dk_total":43}
    def test_t15_freeze_and_immutable(self):
        rows=[self.row(40,-2),self.row(16,-4),self.row(10,-9)]
        self.assertEqual(select(rows,[],self.kickoff-timedelta(minutes=16)),[])
        first=select(rows,[],self.kickoff-timedelta(minutes=15))
        self.assertEqual(first[0]["dk_home_spread"],-4)
        self.assertEqual(first[0]["lock_status"],"official")
        self.assertEqual(first[0]["lock_cutoff_utc"],(self.kickoff-timedelta(minutes=15)).isoformat())
        self.assertEqual(select(rows,first,self.kickoff-timedelta(minutes=2)),first)
    def test_late_scheduled_run_uses_pre_cutoff_only(self):
        rows=[self.row(18,-2),self.row(12,-9)]
        first=select(rows,[],self.kickoff-timedelta(minutes=10))
        self.assertEqual(first[0]["dk_home_spread"],-2)
    def test_rescheduled_lock_is_not_reused_for_new_kickoff(self):
        old={**self.row(20,-3),"lock_status":"official"}
        moved=self.kickoff+timedelta(hours=1)
        now=self.kickoff-timedelta(minutes=5)
        live={"generated_at_utc":(now-timedelta(minutes=5)).isoformat(),
              "games":[{"game_id":"g","kickoff_utc":moved.isoformat(),
                        "projected_margin_home":2,"projected_total":44}]}
        row=freeze(live,[],[old],now)[0]
        self.assertEqual(row["kickoff_utc"],moved.isoformat())
        self.assertEqual(row["lock_status"],"early_pregame")
        self.assertIsNone(row["dk_home_spread"])
        self.assertEqual(freeze(live,[],[old],self.kickoff+timedelta(minutes=5)),[old])

    def live(self, now, games=None):
        game={"game_id":"g","kickoff_utc":self.kickoff.isoformat(),
              "projected_margin_home":2,"projected_total":44}
        return {"generated_at_utc":(now-timedelta(minutes=5)).isoformat(),
                "games":games or [game]}
    def test_no_new_lock_after_kickoff(self):
        self.assertEqual(select([self.row(16,-2)],[],self.kickoff),[])
    def test_pre_cutoff_pair_replaces_early_checkpoint(self):
        old={**self.row(120,-2),"lock_status":"early_pregame"}
        fresh=self.row(18,-5)
        now=self.kickoff-timedelta(minutes=10)
        row=freeze(self.live(now),[fresh],[old],now)[0]
        self.assertEqual(row["lock_status"],"official")
        self.assertEqual(row["dk_home_spread"],-5)
    def test_late_tick_locks_the_quote_it_just_refreshed(self):
        old={**self.row(120,-2),"lock_status":"early_pregame"}
        fresh=self.row(10,-5)
        now=self.kickoff-timedelta(minutes=10)
        row=freeze(self.live(now),[fresh],[old],now)[0]
        self.assertEqual(row["lock_status"],"last_available")
        self.assertEqual(row["dk_home_spread"],-5)
        self.assertEqual(row["lock_cutoff_utc"],(self.kickoff-timedelta(minutes=15)).isoformat())
        self.assertEqual(freeze(self.live(now),[fresh],[row],self.kickoff-timedelta(minutes=4)),[row])
    def test_fresh_final_lock_is_not_replaced(self):
        old={**self.row(25,-4),"lock_status":"last_available"}
        now=self.kickoff-timedelta(minutes=5)
        self.assertEqual(freeze(self.live(now),[self.row(8,-9)],[old],now),[old])
    def test_stale_quote_stays_upgradeable_until_the_final_minutes(self):
        old={**self.row(180,-2),"lock_status":"early_pregame"}
        early=self.kickoff-timedelta(minutes=10)
        row=freeze(self.live(early),[old],[old],early)[0]
        self.assertEqual(row["lock_status"],"early_pregame")
        self.assertEqual(row["dk_home_spread"],-2)
        final=self.kickoff-timedelta(minutes=3)
        locked=freeze(self.live(final),[old],[old],final)[0]
        self.assertEqual(locked["lock_status"],"last_available")
    def test_other_kickoffs_are_not_frozen_early(self):
        later=self.kickoff+timedelta(hours=5)
        other={**self.row(30,-7),"game_id":"later","kickoff_utc":later.isoformat(),
               "lock_status":"early_pregame",
               "captured_at_utc":(later-timedelta(hours=4)).isoformat()}
        now=self.kickoff-timedelta(minutes=10)
        games=[{"game_id":"g","kickoff_utc":self.kickoff.isoformat(),
                "projected_margin_home":2,"projected_total":44},
               {"game_id":"later","kickoff_utc":later.isoformat(),
                "projected_margin_home":1,"projected_total":40}]
        rows=freeze(self.live(now,games),[self.row(18,-5)],[other],now)
        saved={row["game_id"]:row for row in rows}
        self.assertEqual(saved["later"],other)
        self.assertEqual(saved["g"]["lock_status"],"official")
        self.assertEqual(saved["g"]["dk_home_spread"],-5)
    def test_started_game_keeps_its_lock(self):
        old={**self.row(20,-3),"lock_status":"early_pregame"}
        now=self.kickoff+timedelta(minutes=5)
        self.assertEqual(freeze(self.live(now),[self.row(20,-3)],[old],now),[old])
    def test_reject_stale_and_post_cutoff_capture(self):
        rows=[self.row(106,-2),self.row(16,-3,captured_minutes=12),self.row(14,-4)]
        self.assertEqual(select(rows,[],self.kickoff-timedelta(minutes=15)),[])

if __name__=="__main__":unittest.main()
