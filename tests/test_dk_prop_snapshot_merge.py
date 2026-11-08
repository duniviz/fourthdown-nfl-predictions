"""Regression tests for partial DraftKings prop snapshots (no API requests)."""
import datetime as dt
import unittest
from tools.refresh_parlayapi_odds import merge_player_quotes
from live.dk_identity import QuoteIndex

NOW = dt.datetime(2026, 11, 7, 19, tzinfo=dt.timezone.utc)
KICK = "2026-11-08T14:30:00.0000000Z"

def quote(player="Chase Brown", market="player_rushing_yards", line=49.5,
          updated="2026-11-07T16:22:54Z"):
    return {"player": player, "market_key": market, "line": line,
            "home_team": "Atlanta Falcons", "away_team": "Cincinnati Bengals",
            "commence_time": KICK, "last_update": updated,
            "over_price": -110, "under_price": -114}

class MergePlayerQuotesTests(unittest.TestCase):
    def test_retains_missing_standard_market(self):
        saved = quote()
        result = merge_player_quotes([saved], [quote("Bijan Robinson", line=99.5)], NOW)
        self.assertIn(saved, result)
        self.assertEqual(len(result), 2)

    def test_standard_market_line_moves_without_duplicates(self):
        old = quote()
        newer = quote(line=50.5, updated="2026-11-07T18:00:00Z")
        self.assertEqual(merge_player_quotes([old], [newer], NOW), [newer])
        self.assertEqual(merge_player_quotes([newer], [old], NOW), [newer])

    def test_distinct_milestone_thresholds_survive(self):
        a = quote(market="player_rushing_yards_milestones", line=40)
        b = quote(market="player_rushing_yards_milestones", line=60)
        self.assertEqual(len(merge_player_quotes([a], [b], NOW)), 2)

    def test_excludes_spreads_expired_and_future_updates(self):
        spread = quote(market="player_rushing_yards_spread", line=-5.5)
        expired = {**quote(), "commence_time": "2026-11-06T14:30:00Z"}
        future = quote(updated="2026-11-07T20:00:00Z")
        self.assertEqual(merge_player_quotes([], [spread, expired, future], NOW), [])

    def test_does_not_relabel_old_quote_as_fresh(self):
        old = quote()
        result = merge_player_quotes([old], [], NOW)
        self.assertEqual(result[0]["last_update"], old["last_update"])

    def test_same_price_can_be_reverified_without_rewriting_provider_timestamp(self):
        old = quote()
        checked = {**quote(), "observed_at_utc": NOW.isoformat()}
        merged = merge_player_quotes([old], [checked], NOW)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["last_update"], old["last_update"])
        self.assertEqual(merged[0]["observed_at_utc"], NOW.isoformat())
        player = {"player":"Chase Brown","market_key":"player_rushing_yards",
                  "team":"CIN","opponent":"ATL"}
        match = QuoteIndex(merged,NOW).find(player,dt.datetime.fromisoformat(KICK.replace("Z","+00:00")))
        self.assertIsNotNone(match)
        self.assertEqual(match[0], NOW)

if __name__ == "__main__":
    unittest.main()
