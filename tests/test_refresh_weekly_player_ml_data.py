import unittest
from tools.refresh_weekly_player_ml_data import CompletedGamesReader

class Data:
    def __init__(self, rows): self.rows=rows
    def to_dicts(self): return self.rows

class FakeSource:
    def load_schedules(self, seasons):
        return Data([{'game_id':'final','game_type':'REG','home_score':21,'away_score':14},
                     {'game_id':'future','game_type':'REG','home_score':None,'away_score':None}])
    def load_player_stats(self, seasons, summary_level='week'):
        return Data([{'game_id':'final','player_id':'one'},{'game_id':'future','player_id':'two'}])

class CompletedDataTests(unittest.TestCase):
    def test_excludes_incomplete_games(self):
        got=CompletedGamesReader(FakeSource()).load_player_stats([2026]).to_dicts()
        self.assertEqual([r['player_id'] for r in got],['one'])
    def test_rejects_schema_mismatch(self):
        class Bad(FakeSource):
            def load_player_stats(self,seasons,summary_level='week'):return Data([{'player_id':'missing-game-id'}])
        with self.assertRaises(ValueError): CompletedGamesReader(Bad()).load_player_stats([2026])

if __name__=='__main__': unittest.main()
