import unittest
from datetime import datetime, timedelta, timezone
from live.verified_scoreboard_kickoffs import scoreboard_kickoffs


class VerifiedScoreboardKickoffTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 22, 17, 20, tzinfo=timezone.utc)
        self.schedules = [{'game_id': '2026_11_PIT_PHI', 'season': 2026, 'week': 11,
                           'game_type': 'REG', 'gameday': '2026-11-22', 'home_team': 'PHI', 'away_team': 'PIT'}]
        self.event = {'season': {'year': 2026, 'type': 2}, 'week': {'number': 11},
                      'date': '2026-11-22T18:00Z', 'competitions': [
                          {'date': '2026-11-22T18:00Z', 'timeValid': True,
                           'competitors': [{'homeAway': 'home', 'team': {'abbreviation': 'PHI'}},
                                           {'homeAway': 'away', 'team': {'abbreviation': 'PIT'}}]}]}
        self.feed = {'updated_at_utc': self.now.isoformat(), 'events': [self.event]}

    def test_detects_earlier_flex(self):
        result = scoreboard_kickoffs(self.schedules, self.feed, self.now)
        self.assertEqual(result['2026_11_PIT_PHI'], datetime(2026, 11, 22, 18, tzinfo=timezone.utc))

    def test_rejects_stale_future_and_ambiguous_sources(self):
        for delta in (timedelta(hours=-13), timedelta(minutes=1)):
            self.feed['updated_at_utc'] = (self.now + delta).isoformat()
            self.assertEqual(scoreboard_kickoffs(self.schedules, self.feed, self.now), {})
        self.feed['updated_at_utc'] = self.now.isoformat()
        self.feed['events'].append(self.event)
        self.assertEqual(scoreboard_kickoffs(self.schedules, self.feed, self.now), {})

    def test_requires_same_week_and_consistent_event_times(self):
        self.event['week']['number'] = 12
        self.assertEqual(scoreboard_kickoffs(self.schedules, self.feed, self.now), {})
        self.event['week']['number'] = 11
        self.event['competitions'][0]['date'] = '2026-11-22T21:25Z'
        self.assertEqual(scoreboard_kickoffs(self.schedules, self.feed, self.now), {})

    def test_game_already_kicked_off_remains_earlier(self):
        after = self.now + timedelta(hours=1)
        self.assertLess(scoreboard_kickoffs(self.schedules, self.feed, after)['2026_11_PIT_PHI'], after)


if __name__ == '__main__':
    unittest.main()
