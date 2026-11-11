import unittest
from live.player_ml_runtime import forecast, use_projection, MODEL_FAMILY
from tools.train_deployable_player_ml import decide, historical_walk_forward, train


def runtime(active=False):
    return {'family':MODEL_FAMILY,'models':{'passing_yards':{'coefficients':[1.1,0],
             'intercept':0,'trained_season':2026,'trained_week':8}},
            'decisions':{'passing_yards':{'active':active}}}


def observations(candidate=100, baseline=120, weeks=4, n=120):
    result=[]
    for i in range(n):
        week=i%weeks+1
        result.append({'game_id':f'2026_{week:02d}_A_B','player_id':f'p{i}',
            'stat_key':'passing_yards','actual':100,
            'player_ml_pair':{'family':MODEL_FAMILY,'baseline':baseline,'candidate':candidate,
                              'trained_season':2025,'trained_week':18}})
    return result


class DeployableMLTests(unittest.TestCase):
    def test_shadow_first_then_active(self):
        value,shadow=use_projection(runtime(), 'passing_yards', 200,2026,9)
        self.assertEqual(value,200);self.assertEqual(shadow['candidate'],220)
        self.assertEqual(use_projection(runtime(True),'passing_yards',200,2026,9)[0],220)
    def test_future_or_stale_model_fails_closed(self):
        self.assertIsNone(forecast(runtime(True),'passing_yards',200,2026,8))
        self.assertIsNone(forecast(runtime(True),'passing_yards',200,2026,11))
        self.assertEqual(use_projection({},'passing_yards',200,2026,9),(200,None))
    def test_clamp_limits_changes(self):
        r=runtime(True);r['models']['passing_yards']['coefficients']=[9,0]
        self.assertEqual(forecast(r,'passing_yards',200,2026,9),250)
    def test_promote_and_rollback(self):
        good=decide(observations(),{})['passing_yards']
        self.assertTrue(good['active']);self.assertEqual(good['reason'],'promoted')
        bad=decide(observations(candidate=150),{'passing_yards':good})['passing_yards']
        self.assertFalse(bad['active']);self.assertEqual(bad['reason'],'rolled_back')
    def test_small_sample_and_duplicate_do_not_promote(self):
        rows=observations(n=50)
        self.assertFalse(decide(rows,{})['passing_yards']['active'])
        self.assertFalse(decide(rows+rows+rows,{})['passing_yards']['active'])
    def test_same_week_training_cannot_count(self):
        rows=observations()
        for r in rows:r['player_ml_pair']['trained_season']=2026;r['player_ml_pair']['trained_week']=8
        self.assertFalse(decide(rows,{})['passing_yards']['active'])

    def test_historical_walk_forward_can_seed_qualification_without_leakage(self):
        rows=[]
        for week in range(1,11):
            for player in range(50):
                rows.append({'season':2026,'week':week,'market':'passing_yards',
                    'player_id':f'{week}-{player}','new':120,'actual':100})
        result=historical_walk_forward(rows)['passing_yards']
        self.assertTrue(result['eligible'])
        self.assertGreaterEqual(result['paired'],300)
        self.assertGreaterEqual(result['weeks'],4)
        self.assertLess(result['candidate_mae'],result['baseline_mae']*.97)
        activated=decide([],{}, {'passing_yards':result})['passing_yards']
        self.assertTrue(activated['active'])
        self.assertEqual(activated['evidence_source'],'historical_walk_forward')

    def test_historical_duplicate_rows_do_not_count_twice(self):
        rows=[]
        for week in range(1,11):
            for player in range(50):
                row={'season':2026,'week':week,'market':'passing_yards',
                     'player_id':f'{week}-{player}','new':120,'actual':100}
                rows.extend((row,row.copy()))
        result=historical_walk_forward(rows)['passing_yards']
        self.assertFalse(result['eligible'])
        self.assertEqual(result['paired'],0)

    def test_historical_replay_requires_minimum_training_history(self):
        rows=[{'season':2026,'week':week,'market':'passing_yards',
               'player_id':f'{week}-{player}','new':120,'actual':100}
              for week in range(1,3) for player in range(50)]
        result=historical_walk_forward(rows)['passing_yards']
        self.assertFalse(result['eligible'])
        self.assertEqual(result['paired'],0)

    def test_train_and_inference_match(self):
        rows=[{'season':2026,'week':str(i%8+1),'market':'passing_yards','new':str(100+i),'actual':str(110+i)} for i in range(150)]
        model=train(rows)['passing_yards'];r={'family':MODEL_FAMILY,'models':{'passing_yards':model}}
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        expected=make_pipeline(StandardScaler(),Ridge(alpha=100.0)).fit(
            [[float(x['new']),int(x['week'])] for x in rows], [float(x['actual']) for x in rows]).predict([[200,9]])[0]
        expected=round(min(250,max(150,expected)),1)
        self.assertEqual(forecast(r,'passing_yards',200,2026,9),expected)

if __name__=='__main__': unittest.main()

class FrozenPairTests(unittest.TestCase):
    def test_only_saved_by_fifteen_minute_cutoff_and_latest(self):
        from live.player_results import select_frozen_ml_pairs
        def row(saved, forecast, candidate):
            return {'game_id':'2026_09_A_B','player_id':'p','stat_key':'passing_yards',
                    'kickoff_utc':'2026-11-08T18:00:00+00:00',
                    'forecast_captured_at_utc':forecast,'saved_at_utc':saved,
                    'player_ml_shadow':{'candidate':candidate}}
        rows=[row('2026-11-08T17:25:00+00:00','2026-11-08T17:20:00+00:00',100),
              row('2026-11-08T17:40:00+00:00','2026-11-08T17:35:00+00:00',110),
              row('2026-11-08T17:46:00+00:00','2026-11-08T17:30:00+00:00',120)]
        pairs=select_frozen_ml_pairs(rows)
        self.assertEqual(pairs[('2026_09_A_B','p','passing_yards')][1]['candidate'],110)
