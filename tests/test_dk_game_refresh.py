import unittest
from datetime import datetime,timezone,timedelta
from live.dk_game_refresh import parse, history_entry
from tools.refresh_sportsgameodds_backup import merge_game_quotes
from live.game_schedule_match import match_scheduled_game
from live.generate import VERIFIED_KICKOFF_OVERRIDES

class DKGameRefreshTests(unittest.TestCase):
    def test_official_flexed_pit_phi_noon_central(self):
        from zoneinfo import ZoneInfo
        local = datetime.fromisoformat(VERIFIED_KICKOFF_OVERRIDES['2026_11_PIT_PHI'])
        scheduled = local.replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
        self.assertEqual(scheduled, datetime(2026, 11, 22, 18, 0, tzinfo=timezone.utc))
        game = {'game_id': '2026_11_PIT_PHI', 'home': 'PHI', 'away': 'PIT', 'kickoff_utc': scheduled.isoformat()}
        provider = datetime(2026, 11, 22, 18, 1, tzinfo=timezone.utc).isoformat()
        self.assertEqual(match_scheduled_game([game], 'PHI', 'PIT', provider)['game_id'], '2026_11_PIT_PHI')

    def test_official_flexed_jax_nyg_kickoff_matches_provider_time(self):
        from zoneinfo import ZoneInfo
        local = datetime.fromisoformat(VERIFIED_KICKOFF_OVERRIDES["2026_11_JAX_NYG"])
        scheduled = local.replace(tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)
        self.assertEqual(scheduled, datetime(2026, 11, 22, 21, 25, tzinfo=timezone.utc))
        game = {"game_id": "2026_11_JAX_NYG", "home": "NYG", "away": "JAX",
                "kickoff_utc": scheduled.isoformat()}
        provider = datetime(2026, 11, 22, 21, 26, tzinfo=timezone.utc).isoformat()
        self.assertEqual(match_scheduled_game([game], "NYG", "JAX", provider)["game_id"],
                         "2026_11_JAX_NYG")
    def test_provider_kickoff_drift_matches_one_published_game(self):
        kickoff=datetime(2026,11,17,1,15,tzinfo=timezone.utc)
        games=[{"game_id":"LAC_BAL","home":"BAL","away":"LAC","kickoff_utc":kickoff.isoformat()}]
        matched=match_scheduled_game(games,"BAL","LAC",(kickoff+timedelta(minutes=6)).isoformat())
        self.assertEqual(matched["game_id"],"LAC_BAL")
        self.assertIsNone(match_scheduled_game(games,"BAL","LAC",(kickoff+timedelta(minutes=16)).isoformat()))
        self.assertIsNone(match_scheduled_game(games,"BAL","LAC","not-a-time"))

    def test_verified_draftkings_only(self):
        now=datetime(2026,11,8,17,tzinfo=timezone.utc)
        kick=(now+timedelta(hours=1)).isoformat()
        stamp=(now-timedelta(minutes=1)).isoformat()
        event={"id":"e","home_team":"Green Bay Packers","away_team":"Chicago Bears",
            "commence_time":kick,"bookmakers":[
              {"key":"other","last_update":stamp,"markets":[]},
              {"key":"draftkings","last_update":stamp,"markets":[
                {"key":"spreads","outcomes":[{"name":"Green Bay Packers","point":-3.5,"price":-110},{"name":"Chicago Bears","point":3.5,"price":-105}]},
                {"key":"totals","outcomes":[{"name":"Over","point":44.5,"price":105},{"name":"Under","point":44.5,"price":-125}]},
                {"key":"h2h","outcomes":[{"name":"Green Bay Packers","price":-180},{"name":"Chicago Bears","price":155}]}]}]}
        rows=parse({"data":[event]},now)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["home_spread"],-3.5)
        self.assertEqual(rows[0]["total"],44.5)
        self.assertEqual(rows[0]["home_spread_price"],-110)
        self.assertEqual(rows[0]["away_spread_price"],-105)
        self.assertEqual(rows[0]["over_price"],105)
        self.assertEqual(rows[0]["under_price"],-125)
        self.assertEqual(rows[0]["home_moneyline_price"],-180)
        self.assertEqual(rows[0]["away_moneyline_price"],155)
        self.assertEqual(rows[0]["observed_at_utc"],now.isoformat())
        self.assertEqual(rows[0]["updated_at_utc"],stamp)
        history=history_entry(rows[0])
        self.assertEqual(history["captured_at_utc"],now.isoformat())
        self.assertEqual(history["provider_updated_at_utc"],stamp)
        self.assertEqual(history["home_spread_last_verified_at_utc"],stamp)
        self.assertEqual(history["home_spread_observed_at_utc"],now.isoformat())
        event["bookmakers"][1].pop("last_update")
        observed=parse({"data":[event]},now)
        self.assertEqual(len(observed),1)
        self.assertEqual(observed[0]["quote_timestamp_source"],"retrieval")
        self.assertEqual(observed[0]["updated_at_utc"],now.isoformat())
        event["bookmakers"][1]["last_update"]=(now+timedelta(minutes=2)).isoformat()
        future=parse({"data":[event]},now)
        self.assertEqual(len(future),1)
        self.assertEqual(future[0]["quote_timestamp_source"],"retrieval")
        self.assertEqual(future[0]["provider_timestamp_status"],"future")
        self.assertEqual(future[0]["updated_at_utc"],now.isoformat())
        event["commence_time"]=(now-timedelta(minutes=2)).isoformat()
        self.assertEqual(parse({"data":[event]},now),[])

class BackupGameMergeTests(unittest.TestCase):
    def test_backup_refreshes_stale_exact_game_markets(self):
        now=datetime(2026,11,8,17,30,tzinfo=timezone.utc)
        kickoff=now+timedelta(minutes=30)
        old={"home":"IND","away":"DAL","commence_time":kickoff.isoformat(),
             "home_spread":5.5,"total":51.5,"updated_at_utc":(now-timedelta(hours=4)).isoformat(),
             "home_spread_last_verified_at_utc":(now-timedelta(hours=4)).isoformat(),
             "total_last_verified_at_utc":(now-timedelta(hours=4)).isoformat(),
             "home_spread_observed_at_utc":(now-timedelta(hours=4)).isoformat(),
             "total_observed_at_utc":(now-timedelta(hours=4)).isoformat(),
             "source_provider":"ParlayAPI"}
        update={"home":"IND","away":"DAL","commence_time":kickoff.isoformat(),
                "home_spread":4.5,"total":51.5,"updated_at_utc":(now-timedelta(minutes=45)).isoformat(),
                "home_spread_last_verified_at_utc":(now-timedelta(minutes=45)).isoformat(),
                "total_last_verified_at_utc":(now-timedelta(minutes=45)).isoformat(),
                "home_spread_observed_at_utc":now.isoformat(),"total_observed_at_utc":now.isoformat(),
                "observed_at_utc":now.isoformat(),"source_provider":"SportsGameOdds"}
        rows,count=merge_game_quotes([old],[update],now)
        self.assertEqual(count,2)
        self.assertEqual(rows[0]["home_spread"],4.5)
        self.assertEqual(rows[0]["total"],51.5)
        self.assertEqual(rows[0]["home_spread_observed_at_utc"],now.isoformat())
        self.assertEqual(rows[0]["total_observed_at_utc"],now.isoformat())
        self.assertEqual(rows[0]["home_spread_last_verified_at_utc"],update["home_spread_last_verified_at_utc"])

    def test_backup_does_not_replace_fresh_primary_quote(self):
        now=datetime(2026,11,8,17,30,tzinfo=timezone.utc)
        kickoff=now+timedelta(minutes=30)
        fresh=(now-timedelta(minutes=5)).isoformat()
        old={"home":"IND","away":"DAL","commence_time":kickoff.isoformat(),
             "home_spread":4.5,"total":51.5,"updated_at_utc":fresh,
             "home_spread_observed_at_utc":fresh,"total_observed_at_utc":fresh,
             "source_provider":"ParlayAPI"}
        update={"home":"IND","away":"DAL","commence_time":kickoff.isoformat(),
                "home_spread":3.5,"total":50.5,"updated_at_utc":now.isoformat(),
                "home_spread_last_verified_at_utc":now.isoformat(),"total_last_verified_at_utc":now.isoformat(),
                "home_spread_observed_at_utc":now.isoformat(),"total_observed_at_utc":now.isoformat(),
                "observed_at_utc":now.isoformat(),"source_provider":"SportsGameOdds"}
        rows,count=merge_game_quotes([old],[update],now)
        self.assertEqual(count,0)
        self.assertEqual(rows[0]["home_spread"],4.5)
        self.assertEqual(rows[0]["total"],51.5)

if __name__=="__main__":
    unittest.main()
