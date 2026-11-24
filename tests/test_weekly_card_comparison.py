import unittest
from tools.weekly_card_comparison import build, pick_result, hit_summary

class WeeklyCardComparisonTests(unittest.TestCase):
    def test_pick_grading_push_no_pick_and_spread_direction(self):
        self.assertEqual(pick_result('game_margin_home',7,10,-3.5),'hit')
        self.assertEqual(pick_result('game_margin_home',2,10,-3.5),'miss')
        self.assertEqual(pick_result('game_total',47,44,44),'push')
        self.assertEqual(pick_result('game_total',44,47,44),'no_pick')
        self.assertEqual(pick_result('game_total',47,44,None),'unavailable')
        rows=[{'result':x} for x in ('hit','miss','push','no_pick','unavailable')]
        self.assertEqual(hit_summary(rows,'result'),{'hits':1,'misses':1,'pushes':1,'no_picks':1,'unavailable':1,'hit_pct':50.0})

    def test_line_must_be_observed_before_saved_lock(self):
        self.lock.update({'dk_total':44.5,'dk_at_utc':'2026-11-20T00:52:00+00:00'})
        market=build([self.game],[self.lock],[],[],[],[self.batch])['weeks'][0]['markets'][0]
        self.assertEqual(market['regular_hits']['hit_pct'],100.0)
        self.assertEqual(market['ml_hits']['hit_pct'],0.0)
        self.lock['dk_at_utc']='2026-11-20T00:54:00+00:00'
        market=build([self.game],[self.lock],[],[],[],[self.batch])['weeks'][0]['markets'][0]
        self.assertEqual(market['regular_hits']['unavailable'],1)
        self.assertIsNone(market['regular_hits']['hit_pct'])
    def setUp(self):
        self.gid='2026_11_IND_HOU'; self.kick='2026-11-20T01:15:00+00:00'
        self.forecast='2026-11-19T23:46:00+00:00'; self.saved='2026-11-20T00:53:00+00:00'
        self.game={'game_id':self.gid,'home_score':26,'away_score':3}
        self.lock={'game_id':self.gid,'away':'IND','home':'HOU','kickoff_utc':self.kick,'forecast_at_utc':self.forecast,'captured_at_utc':self.saved,'lock_status':'last_available','projected_margin_home':6.85,'projected_total':43.43,'game_ml_shadow':{'markets':{'game_margin_home':{'candidate':9.69},'game_total':{'candidate':47.43}}}}
        self.batch={'game_id':self.gid,'player_id':'GAME','market':'game_total','kickoff_utc':self.kick,'generated_at_utc':'2026-11-20T00:00:00+00:00','predictions':{'current':47.43,'ridge':45},'selected':None}

    def test_game_compares_frozen_card_estimates(self):
        d=build([self.game],[self.lock],[],[],[],[self.batch]); m=d['weeks'][0]['markets'][0]
        self.assertEqual((m['market'],m['winner'],m['samples']),('game_total','regular',1))
        self.assertEqual((m['details'][0]['actual'],m['regular_mae'],m['ml_mae']),(29,14.43,18.43))

    def test_selected_algorithm_and_missing_or_late_evidence(self):
        self.batch['selected']={'model':'ridge','samples':4}
        d=build([self.game],[self.lock],[],[],[],[self.batch]);self.assertEqual(d['weeks'][0]['markets'][0]['details'][0]['ml'],45)
        self.batch['generated_at_utc']=self.kick
        self.assertEqual(build([self.game],[self.lock],[],[],[],[self.batch])['weeks'],[])
        self.assertEqual(build([self.game],[self.lock],[],[],[],[])['weeks'],[])

    def test_saved_game_shadow_is_reported_separately_from_late_batch(self):
        self.batch['generated_at_utc']='2026-11-20T01:00:00+00:00'
        report=build([self.game],[self.lock],[],[],[],[self.batch])
        self.assertEqual(report['weeks'],[])
        group=next(m for m in report['game_shadow_comparisons'][0]['markets'] if m['market']=='game_total')
        self.assertEqual((group['samples'],group['regular_mae'],group['shadow_mae']),(1,14.43,18.43))
        self.lock['captured_at_utc']=self.kick
        self.assertEqual(build([self.game],[self.lock],[],[],[],[self.batch])['game_shadow_comparisons'],[])

    def test_older_saved_batch_survives_a_later_refresh(self):
        later={**self.batch,'generated_at_utc':'2026-11-20T01:00:00+00:00'}
        report=build([self.game],[self.lock],[],[],[],[later,self.batch])
        self.assertEqual(report['weeks'][0]['markets'][0]['ml_mae'],18.43)
        conflict={**self.batch,'selected':{'model':'ridge','samples':4}}
        self.assertEqual(build([self.game],[self.lock],[],[],[],[self.batch,conflict])['weeks'],[])
        recovered={**self.batch,'published_at_utc':'2026-11-20T00:54:00+00:00'}
        self.assertEqual(build([self.game],[self.lock],[],[],[],[recovered])['weeks'],[])
        recovered['published_at_utc']='2026-11-20T00:01:00+00:00'
        self.assertEqual(build([self.game],[self.lock],[],[],[],[recovered])['weeks'][0]['markets'][0]['samples'],1)

    def test_player_requires_matching_history_snapshot_and_same_actual(self):
        snap={'game_id':self.gid,'player_id':'p','player':'Player','market':'player_rush_yds','kickoff':self.kick,'captured_at':self.forecast,'saved_at_utc':self.saved,'projection':42}
        hist={'game_id':self.gid,'player_id':'p','stat_key':'rushing_yards','forecast_captured_at_utc':self.forecast,'saved_at_utc':self.saved,'projection':42,'player_ml_shadow':{'candidate':41.6}}
        actual={'game_id':self.gid,'player_id':'p','stat_key':'rushing_yards','projection':42,'actual':50}
        batch={'game_id':self.gid,'player_id':'p','market':'rushing_yards','generated_at_utc':'2026-11-20T00:00:00+00:00','predictions':{'current':41.6},'selected':None}
        snap.update({'dk_line':45.5,'dk_captured_at':'2026-11-20T00:52:00+00:00'})
        d=build([],[],[actual],[snap],[hist],[batch]);self.assertEqual(d['weeks'][0]['markets'][0]['winner'],'regular')
        self.assertEqual(d['weeks'][0]['markets'][0]['regular_hits']['misses'],1)
        self.assertEqual(d['weeks'][0]['markets'][0]['ml_hits']['misses'],1)
        actual['projection']=41
        self.assertEqual(build([],[],[actual],[snap],[hist],[batch])['weeks'],[])
        actual['projection']=42;batch['predictions']['current']=30
        self.assertEqual(build([],[],[actual],[snap],[hist],[batch])['weeks'],[])

if __name__=='__main__': unittest.main()

