import unittest
from datetime import datetime,timezone,timedelta
from live.lock_pregame_props import match_quote

class PregameSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,1,12,tzinfo=timezone.utc)
        self.player={"player":"Josh Allen","team":"BUF","opponent":"BAL","market":"Passing yards"}
        self.quote={"player":"Josh Allen","market_key":"player_pass_yds","line":252.5,
                    "home_team":"Buffalo Bills","away_team":"Baltimore Ravens",
                    "commence_time":(self.now+timedelta(hours=6)).isoformat(),
                    "last_update":(self.now-timedelta(minutes=5)).isoformat()}
    def test_match_verified_pregame_line(self):
        self.assertEqual(match_quote(self.player,[self.quote],self.now)[3],252.5)
    def test_no_postkickoff_line(self):
        q={**self.quote,"commence_time":(self.now-timedelta(minutes=1)).isoformat()}
        self.assertIsNone(match_quote(self.player,[q],self.now))
    def test_no_other_matchup(self):
        q={**self.quote,"away_team":"Miami Dolphins"}
        self.assertIsNone(match_quote(self.player,[q],self.now))
    def test_no_future_quote(self):
        q={**self.quote,"last_update":(self.now+timedelta(minutes=5)).isoformat()}
        self.assertIsNone(match_quote(self.player,[q],self.now))
    def test_latest_quote_wins(self):
        older={**self.quote,"line":249.5,"last_update":(self.now-timedelta(hours=2)).isoformat()}
        self.assertEqual(match_quote(self.player,[older,self.quote],self.now)[3],252.5)

if __name__=="__main__": unittest.main()
