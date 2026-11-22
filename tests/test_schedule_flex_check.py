import unittest
from datetime import datetime, timedelta, timezone
from live.schedule_flex_check import changed_games


class FlexWakeTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 22, 17, 20, tzinfo=timezone.utc)
        self.live = {'games': [{'game_id': '2026_11_PIT_PHI', 'season': 2026, 'week': 11,
                                'home': 'PHI', 'away': 'PIT', 'kickoff_utc': '2026-11-22T21:25Z'}]}
        self.event = {'season': {'year': 2026, 'type': 2}, 'week': {'number': 11},
                      'date': '2026-11-22T18:00Z', 'competitions': [{'date': '2026-11-22T18:00Z',
                      'competitors': [{'homeAway': 'home', 'team': {'abbreviation': 'PHI'}},
                                      {'homeAway': 'away', 'team': {'abbreviation': 'PIT'}}]}]}
        self.feed = {'updated_at_utc': self.now.isoformat(), 'events': [self.event]}

    def test_changed_future_kickoff_wakes(self):
        self.assertEqual(changed_games(self.live, self.feed, self.now), ['2026_11_PIT_PHI'])

    def test_unchanged_stale_or_ambiguous_does_not_wake(self):
        self.live['games'][0]['kickoff_utc'] = self.event['date']
        self.assertEqual(changed_games(self.live, self.feed, self.now), [])
        self.live['games'][0]['kickoff_utc'] = '2026-11-22T21:25Z'
        self.feed['updated_at_utc'] = (self.now - timedelta(hours=13)).isoformat()
        self.assertEqual(changed_games(self.live, self.feed, self.now), [])
        self.feed['updated_at_utc'] = self.now.isoformat()
        self.feed['events'].append(self.event)
        self.assertEqual(changed_games(self.live, self.feed, self.now), [])

    def test_no_late_refresh_after_or_close_to_kickoff(self):
        self.assertEqual(changed_games(self.live, self.feed, self.now + timedelta(minutes=26)), [])
        self.live['games'][0]['kickoff_utc'] = '2026-11-22T17:10Z'
        self.assertEqual(changed_games(self.live, self.feed, self.now), [])


if __name__ == '__main__':
    unittest.main()
