import unittest
from datetime import datetime, timezone
from scripts.advanced_ml_slate_guard import should_publish, should_refresh


class AdvancedSlateGuardTests(unittest.TestCase):
    def setUp(self):
        self.slate = {'season': 2026, 'week': 11, 'games': [{'game_id': 'g'}]}
        self.players = {'season': 2026, 'week': 11, 'players': [{'player_id': 'p'}],
                        'generated_at_utc': '2026-11-17T12:00:00Z'}
        self.runtime = {'family': 'free-nfl-advanced-ridge-v1', 'research_only': True,
                        'target_season': 2026, 'target_week': 11,
                        'generated_at_utc': '2026-11-17T13:00:00Z', 'models': {'rushing': {}}}
        self.features = {**self.runtime, 'players': {'p': {}}}
        self.now = datetime(2026, 11, 17, 14, tzinfo=timezone.utc)

    def test_slate_change_refreshes_once(self):
        old = {**self.runtime, 'target_week': 10}
        self.assertTrue(should_refresh(self.slate, self.players, old, self.features))
        self.assertFalse(should_refresh(self.slate, self.players, self.runtime, self.features))
        self.assertFalse(should_refresh(self.slate, {**self.players, 'week': 10}, old, self.features))

    def test_publish_only_new_matching_features(self):
        self.assertTrue(should_publish(self.slate, self.players, self.runtime, self.features, self.now))
        self.assertFalse(should_publish(self.slate, {**self.players, 'generated_at_utc': '2026-11-17T13:01:00Z'}, self.runtime, self.features, self.now))
        self.assertFalse(should_publish(self.slate, self.players, self.runtime, {**self.features, 'target_week': 10}, self.now))
        self.assertFalse(should_publish(self.slate, self.players, self.runtime, self.features, datetime(2026, 11, 17, 12, 30, tzinfo=timezone.utc)))

    def test_invalid_or_missing_sources_fail_closed(self):
        self.assertFalse(should_publish(self.slate, self.players, self.runtime, {}, self.now))
        self.assertFalse(should_refresh({}, self.players, {}, {}))
        self.assertFalse(should_publish(self.slate, {**self.players, 'generated_at_utc': 'bad'}, self.runtime, self.features, self.now))


if __name__ == '__main__':
    unittest.main()
