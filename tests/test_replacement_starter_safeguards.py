import unittest
from scripts.refresh_starters import collect_depth_rows
from live.projection_audit import audit

class ReplacementSafeguardTests(unittest.TestCase):
    def test_tight_end_depth_chart(self):
        payload={'name':'Tight End','athletes':[{'rank':1,'athlete':{'displayName':'Test Tight End'}}]}
        self.assertEqual(collect_depth_rows(payload)['TE'], ['Test Tight End'])

    def test_nested_espn_position(self):
        payload={"position":{"abbreviation":"WR"},"athletes":[{"rank":1,"athlete":{"displayName":"Test Receiver"}}]}
        self.assertEqual(collect_depth_rows(payload)["WR"], ["Test Receiver"])

    def test_limited_starter_is_flagged_without_changing_projection(self):
        player={'game_id':'g','player_id':'p','player':'QB','position':'QB','stat_key':'passing_yards','projection':130,'games_used':2,'starter_status':'confirmed_starter','expected_opportunities':19}
        report=audit([player])
        self.assertIn('qb_starter_limited_history',[x['code'] for x in report['flags']])
        self.assertEqual(player['projection'],130)

    def test_unconfirmed_or_missing_history_is_not_labeled(self):
        p={'game_id':'g','player_id':'p','player':'QB','position':'QB','stat_key':'passing_yards','projection':130,'starter_status':'unconfirmed'}
        self.assertNotIn('qb_starter_limited_history',[x['code'] for x in audit([p])['flags']])

if __name__=='__main__': unittest.main()

class FreezeStarterFeedTests(unittest.TestCase):
    def test_frozen_game_rows_remain_unchanged(self):
        import json
        from datetime import datetime, timedelta, timezone
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from scripts import refresh_starters
        with TemporaryDirectory() as tmp:
            feed=Path(tmp)/'starters.json'; forecast=Path(tmp)/'forecast.json'
            row={'game_id':'game','team':'A','position':'QB','status':'projected','player':'Old QB'}
            feed.write_text(json.dumps({'starters':[row]}))
            forecast.write_text(json.dumps({'season':2026,'week':1,'games':[{'game_id':'game','home':'A','away':'B','kickoff_utc':(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()}]}))
            with patch.object(refresh_starters,'FEED',feed), patch.object(refresh_starters,'FORECAST',forecast), patch.object(refresh_starters,'fetch_espn_teams',return_value={'A':'1','B':'2'}), patch.object(refresh_starters,'fetch_depth_chart') as fetch:
                refresh_starters.main()
                fetch.assert_not_called()
            self.assertEqual(json.loads(feed.read_text())['starters'],[row])
