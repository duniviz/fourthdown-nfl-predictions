import unittest
from collections import defaultdict

from research.pbp_situational_features import add_situational_features, load_completed_pbp
from research.free_nfl_feature_lab import complete_lagged_values
from research.publish_advanced_player_ml import features_for_player


class SituationalFeaturesTest(unittest.TestCase):
    def test_loader_excludes_unfinished_and_duplicate_plays(self):
        try:
            import polars as pl
        except ImportError:
            self.skipTest('polars is installed in the NFL data workflow')
        base = dict(season=2026, week=3, season_type='REG', play_type='run',
                    passer_player_id=None, receiver_player_id=None, rusher_player_id='rb',
                    yardline_100=20, air_yards=None, yards_gained=5)
        rows = [dict(base, game_id='finished', play_id=1),
                dict(base, game_id='finished', play_id=2),
                dict(base, game_id='finished', play_id=2),
                dict(base, game_id='unfinished', play_id=1)]
        class Feed:
            def load_pbp(self, seasons):
                return pl.DataFrame(rows)
        selected = load_completed_pbp(Feed(), 2026, {'finished'})
        self.assertEqual([(r['game_id'], r['play_id']) for r in selected], [('finished', 1)])

    def test_rates_and_future_week_exclusion(self):
        series = defaultdict(list)
        rows = [
            dict(season=2026, week=3, season_type='REG', play_type='run', rusher_player_id='rb', yardline_100=10, yards_gained=0),
            dict(season=2026, week=3, season_type='REG', play_type='run', rusher_player_id='rb', yardline_100=50, yards_gained=12),
            dict(season=2026, week=4, season_type='REG', play_type='run', rusher_player_id='rb', yardline_100=1, yards_gained=15),
            dict(season=2026, week=3, season_type='REG', play_type='pass', passer_player_id='qb', receiver_player_id='wr', yardline_100=15, air_yards=25),
            dict(season=2026, week=3, season_type='REG', play_type='pass', passer_player_id='qb', receiver_player_id='wr', yardline_100=50, air_yards=5),
        ]
        add_situational_features(series, rows)
        self.assertEqual(complete_lagged_values(series, 'situational_rushing_yards', 'rb', (2026, 4), 3), ([0.5, 0.5, 0.5], 1.0))
        self.assertEqual(complete_lagged_values(series, 'situational_receiving_yards', 'wr', (2026, 4), 3), ([0.5, 0.5, 15.0], 1.0))
        feature = features_for_player(series, {}, 'rb', 'rushing_yards', (2026, 4), 'IND')
        self.assertEqual(feature['situational'], [0.5, 0.5, 0.5, 1.0])
        self.assertEqual(complete_lagged_values(series, 'situational_rushing_yards', 'rb', (2026, 3), 3)[1], 0.0)

    def test_missing_input_not_converted_to_a_zero_rate(self):
        series = defaultdict(list)
        add_situational_features(series, [dict(season=2026, week=3, season_type='REG',
            play_type='pass', passer_player_id='qb', yardline_100=10, air_yards=None)])
        self.assertEqual(complete_lagged_values(series, 'situational_passing_yards', 'qb', (2026, 4), 3)[1], 0.0)


if __name__ == '__main__':
    unittest.main()
