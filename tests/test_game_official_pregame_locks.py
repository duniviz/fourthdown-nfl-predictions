import unittest
from datetime import datetime,timedelta,timezone
from live.game_official_pregame_locks import select

class OfficialGameLockTests(unittest.TestCase):
    def test_selects_latest_eligible_and_never_replaces(self):
        kickoff=datetime(2026,11,8,18,tzinfo=timezone.utc)
        def row(minutes,spread):
            stamp=(kickoff-timedelta(minutes=minutes)).isoformat()
            return {"game_id":"g","kickoff_utc":kickoff.isoformat(),
                    "forecast_at_utc":stamp,"dk_at_utc":stamp,
                    "projected_margin_home":2,"projected_total":44,
                    "dk_home_spread":spread,"dk_total":43}
        rows=[row(110,-1),row(40,-2),row(20,-3)]
        self.assertEqual(select(rows,[],kickoff-timedelta(minutes=1)),[])
        first=select(rows,[],kickoff)
        self.assertEqual(len(first),1)
        self.assertEqual(first[0]["dk_home_spread"],-2)
        self.assertEqual(select([row(31,-4)],first,kickoff+timedelta(hours=1)),first)
    def test_rejects_stale_and_post_cutoff(self):
        kickoff=datetime(2026,11,8,18,tzinfo=timezone.utc)
        def row(minutes):
            t=(kickoff-timedelta(minutes=minutes)).isoformat()
            return {"game_id":str(minutes),"kickoff_utc":kickoff.isoformat(),
                    "forecast_at_utc":t,"dk_at_utc":t,
                    "projected_margin_home":2,"projected_total":44,"dk_total":45}
        self.assertEqual(select([row(121),row(29)],[],kickoff),[])

if __name__=="__main__":
    unittest.main()
