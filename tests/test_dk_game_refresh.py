import unittest
from datetime import datetime,timezone,timedelta
from live.dk_game_refresh import parse

class DKGameRefreshTests(unittest.TestCase):
    def test_verified_draftkings_only(self):
        now=datetime(2026,11,8,17,tzinfo=timezone.utc)
        kick=(now+timedelta(hours=1)).isoformat()
        stamp=(now-timedelta(minutes=1)).isoformat()
        event={"id":"e","home_team":"Green Bay Packers","away_team":"Chicago Bears",
            "commence_time":kick,"bookmakers":[
              {"key":"other","last_update":stamp,"markets":[]},
              {"key":"draftkings","last_update":stamp,"markets":[
                {"key":"spreads","outcomes":[{"name":"Green Bay Packers","point":-3.5}]},
                {"key":"totals","outcomes":[{"name":"Over","point":44.5}]}]}]}
        rows=parse({"data":[event]},now)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["home_spread"],-3.5)
        self.assertEqual(rows[0]["total"],44.5)
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

if __name__=="__main__":
    unittest.main()
