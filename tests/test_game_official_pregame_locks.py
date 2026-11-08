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

    def test_no_new_lock_after_kickoff(self):
        self.assertEqual(select([self.row(16,-2)],[],self.kickoff),[])
    def test_reject_stale_and_post_cutoff_capture(self):
        rows=[self.row(106,-2),self.row(16,-3,captured_minutes=12),self.row(14,-4)]
        self.assertEqual(select(rows,[],self.kickoff-timedelta(minutes=15)),[])

if __name__=="__main__":unittest.main()
