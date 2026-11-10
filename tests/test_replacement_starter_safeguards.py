import unittest
from scripts.refresh_starters import collect_depth_rows
from live.projection_audit import audit

class ReplacementSafeguardTests(unittest.TestCase):
    def test_tight_end_depth_chart(self):
        payload={'name':'Tight End','athletes':[{'rank':1,'athlete':{'displayName':'Test Tight End'}}]}
        self.assertEqual(collect_depth_rows(payload)['TE'], ['Test Tight End'])

    def test_limited_starter_is_flagged_without_changing_projection(self):
        player={'game_id':'g','player_id':'p','player':'QB','position':'QB','stat_key':'passing_yards','projection':130,'games_used':2,'starter_status':'confirmed_starter','expected_opportunities':19}
        report=audit([player])
        self.assertIn('qb_starter_limited_history',[x['code'] for x in report['flags']])
        self.assertEqual(player['projection'],130)

    def test_unconfirmed_or_missing_history_is_not_labeled(self):
        p={'game_id':'g','player_id':'p','player':'QB','position':'QB','stat_key':'passing_yards','projection':130,'starter_status':'unconfirmed'}
        self.assertNotIn('qb_starter_limited_history',[x['code'] for x in audit([p])['flags']])

if __name__=='__main__': unittest.main()
