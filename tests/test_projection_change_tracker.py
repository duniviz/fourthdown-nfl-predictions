import unittest
from datetime import datetime, timezone
from tools.projection_change_tracker import build

class ProjectionChangesTests(unittest.TestCase):
    def test_only_unique_saved_prelock_versions_and_real_ids(self):
        games=[{'game_id':'G','kickoff_utc':'2026-11-12T20:00:00Z'}]
        def g(at,saved,home=20,away=17):
            return {'game_id':'G','forecast_at_utc':at,'captured_at_utc':saved,'projected_home_score':home,'projected_away_score':away}
        def p(at,saved,value,player='1'):
            return {'game_id':'G','player_id':player,'stat_key':'passing_yards','forecast_captured_at_utc':at,'saved_at_utc':saved,'projection':value}
        a='2026-11-10T10:00:00Z'; b='2026-11-11T10:00:00Z'; c='2026-11-12T19:46:00Z'
        output=build(games,[g(a,a),g(a,b),g(b,b,21),g(c,c,99)],
                     [p(a,a,200),p(a,b,200),p(b,b,220),p(c,c,999),p(b,b,100,'2')],datetime(2026,11,13,tzinfo=timezone.utc))
        self.assertEqual([x['home'] for x in output['games']['G']],[20,21])
        self.assertEqual([x['value'] for x in output['players']['G|1|passing_yards']],[200,220])
        self.assertEqual(output['players']['G|2|passing_yards'][0]['value'],100)
    def test_requires_real_saved_timestamp_and_rejects_bad_values(self):
        games=[{'game_id':'G','kickoff_utc':'2026-11-12T20:00:00Z'}]
        rows=[{'game_id':'G','player_id':'1','stat_key':'receptions','projection':None,'forecast_captured_at_utc':'2026-11-10T00:00:00Z','saved_at_utc':'2026-11-10T00:00:00Z'},
              {'game_id':'G','player_id':'1','stat_key':'receptions','projection':3,'forecast_captured_at_utc':'2026-11-10T00:00:00Z'}]
        self.assertEqual(build(games,[],rows,datetime(2026,11,13,tzinfo=timezone.utc))['players'],{})
