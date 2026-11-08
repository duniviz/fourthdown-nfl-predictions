import unittest
from datetime import datetime, timezone, timedelta
from live.game_pregame_observations import collect
from live.game_official_pregame_locks import select

class GameObservationTests(unittest.TestCase):
    def test_freezes_only_valid_pregame_quote_and_is_idempotent(self):
        now=datetime(2026,11,8,18,tzinfo=timezone.utc)
        kickoff=(now+timedelta(minutes=30)).isoformat()
        stamp=(now-timedelta(minutes=5)).isoformat()
        game={"game_id":"g1","season":2026,"week":10,"home":"GB","away":"CHI",
              "kickoff_utc":kickoff,"_forecast_generated_at":stamp,
              "projected_margin_home":4,"projected_total":45,"predicted_winner":"GB"}
        quote={"bookmaker":"draftkings","home":"GB","away":"CHI",
               "commence_time":kickoff,"updated_at_utc":stamp,
               "home_spread":-3.5,"total":44.5}
        first=collect([game],[quote],[],now)
        self.assertEqual(len(first),1)
        self.assertEqual(first[0]["dk_home_spread"],-3.5)
        self.assertEqual(collect([game],[quote],first,now),first)
        bad={**quote,"updated_at_utc":(now+timedelta(minutes=1)).isoformat()}
        self.assertEqual(collect([game],[bad],[],now),[])
        late={**game,"_forecast_generated_at":(now+timedelta(minutes=1)).isoformat()}
        self.assertEqual(collect([late],[quote],[],now),[])

    def test_requires_draftkings_and_valid_market(self):
        now=datetime(2026,11,8,18,tzinfo=timezone.utc)
        kickoff=(now+timedelta(hours=1)).isoformat()
        stamp=(now-timedelta(minutes=1)).isoformat()
        game={"game_id":"g","home":"GB","away":"CHI","kickoff_utc":kickoff,
              "_forecast_generated_at":stamp,"projected_margin_home":1,"projected_total":40}
        quote={"bookmaker":"other","home":"GB","away":"CHI","commence_time":kickoff,
               "updated_at_utc":stamp,"home_spread":-1,"total":41}
        self.assertEqual(collect([game],[quote],[],now),[])
        self.assertEqual(collect([game],[{**quote,"bookmaker":"draftkings","home_spread":None,"total":None}],[],now),[])

    def test_recently_checked_unchanged_market_is_fresh_but_keeps_book_timestamp(self):
        now=datetime(2026,11,8,18,tzinfo=timezone.utc)
        kickoff=(now+timedelta(minutes=30)).isoformat()
        forecast=(now-timedelta(minutes=5)).isoformat()
        provider_update=(now-timedelta(hours=5)).isoformat()
        game={"game_id":"g1","home":"GB","away":"CHI","kickoff_utc":kickoff,
              "_forecast_generated_at":forecast,"projected_margin_home":4,"projected_total":45}
        quote={"bookmaker":"draftkings","home":"GB","away":"CHI","commence_time":kickoff,
               "updated_at_utc":provider_update,"observed_at_utc":now.isoformat(),
               "home_spread":-3.5,"total":44.5,
               "home_spread_last_verified_at_utc":provider_update,"total_last_verified_at_utc":provider_update,
               "home_spread_observed_at_utc":now.isoformat(),"total_observed_at_utc":now.isoformat()}
        row=collect([game],[quote],[],now)[0]
        self.assertEqual(row["dk_at_utc"],now.isoformat())
        self.assertEqual(row["dk_total_updated_at_utc"],provider_update)
        lock_time=now+timedelta(minutes=15)
        official=select([row],[],lock_time)
        self.assertEqual(official[0]["lock_status"],"official")
        self.assertEqual(official[0]["dk_total_updated_at_utc"],provider_update)

    def test_one_stale_game_market_makes_combined_observation_stale(self):
        now=datetime(2026,11,8,18,tzinfo=timezone.utc)
        kickoff=(now+timedelta(minutes=30)).isoformat()
        forecast=(now-timedelta(minutes=5)).isoformat()
        stale=(now-timedelta(hours=2)).isoformat()
        game={"game_id":"g1","home":"GB","away":"CHI","kickoff_utc":kickoff,
              "_forecast_generated_at":forecast,"projected_margin_home":4,"projected_total":45}
        quote={"bookmaker":"draftkings","home":"GB","away":"CHI","commence_time":kickoff,
               "updated_at_utc":now.isoformat(),"observed_at_utc":now.isoformat(),
               "home_spread":-3.5,"total":44.5,
               "home_spread_observed_at_utc":now.isoformat(),"total_observed_at_utc":stale}
        row=collect([game],[quote],[],now)[0]
        self.assertEqual(row["dk_at_utc"],stale)
        self.assertEqual(select([row],[],now+timedelta(minutes=15)),[])

if __name__=="__main__":
    unittest.main()
