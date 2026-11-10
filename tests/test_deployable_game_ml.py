import unittest
from live.game_ml_runtime import apply, FAMILY
from tools.train_deployable_game_ml import decide,pairs

def game():
    form={'results':[{'points_for':24,'points_against':20} for _ in range(5)]}
    return {'season':2026,'week':10,'home':'A','away':'B','projected_margin_home':3.0,'projected_total':44.0,
            'analysis':{'home':{'recent_form':form},'away':{'recent_form':form}}}
def runtime(active):
    return {'family':FAMILY,'models':{'game_margin_home':{'coefficients':[0,0,0,0,0],'intercept':5,'trained_season':2026,'trained_week':9},
        'game_total':{'coefficients':[0,0,0,0,0],'intercept':48,'trained_season':2026,'trained_week':9}},
        'decisions':{k:{'active':active} for k in ('game_margin_home','game_total')}}

def samples(bad=False):
    return [{'game_id':f'2026_{i%6+1:02d}_G{i}','week':(2026,i%6+1),'market':market,
             'baseline':4 if market=='game_margin_home' else 44,'candidate':(12 if bad else 7) if market=='game_margin_home' else (60 if bad else 50),
             'actual':7 if market=='game_margin_home' else 50,'spread':-2,'line':42}
            for market in ('game_margin_home','game_total') for i in range(120)]

class GameMLTests(unittest.TestCase):
    def test_shadow_and_active_with_scores(self):
        g=apply(game(),runtime(False));self.assertEqual(g['projected_margin_home'],3);self.assertEqual(g['game_ml_shadow']['markets']['game_total']['candidate'],48)
        g=apply(game(),runtime(True));self.assertEqual(g['projected_margin_home'],5);self.assertEqual(g['projected_total'],48);self.assertEqual(g['predicted_winner'],'A')
    def test_stale_and_same_week_fallback(self):
        r=runtime(True);r['models']['game_margin_home']['trained_week']=10;r['models']['game_total']['trained_week']=10
        self.assertNotIn('game_ml_shadow',apply(game(),r))
        r['models']['game_margin_home']['trained_week']=7;r['models']['game_total']['trained_week']=7
        self.assertNotIn('game_ml_shadow',apply(game(),r))
    def test_promote_and_rollback(self):
        initial=decide(samples(),{})
        self.assertTrue(initial['game_margin_home']['active']);self.assertTrue(initial['game_total']['active'])
        changed=decide(samples(True),initial)
        self.assertEqual(changed['game_margin_home']['reason'],'rolled_back');self.assertFalse(changed['game_total']['active'])
    def test_pick_regression_blocks_promotion(self):
        rows=samples()
        for r in rows:
            if r['market']=='game_margin_home':r.update(baseline=5,candidate=-.1,actual=.1,spread=0)
        self.assertFalse(decide(rows,{})['game_margin_home']['active'])
    def test_frozen_pairs_require_cutoff_and_same_game(self):
        shadow={'family':FAMILY,'markets':{'game_margin_home':{'baseline':3,'candidate':5,'trained_season':2026,'trained_week':8}}}
        base={'game_id':'2026_09_A_B','season':2026,'week':9,'home':'A','away':'B','kickoff_utc':'2026-11-08T18:00:00+00:00',
              'forecast_at_utc':'2026-11-08T17:30:00+00:00','captured_at_utc':'2026-11-08T17:40:00+00:00','dk_at_utc':'2026-11-08T17:39:00+00:00',
              'dk_home_spread':-3,'game_ml_shadow':shadow}
        actual={'game_id':base['game_id'],'home':'A','away':'B','home_score':24,'away_score':17}
        self.assertEqual(len(pairs([base],[actual])),1)
        self.assertEqual(len(pairs([{**base,'captured_at_utc':'2026-11-08T17:46:00+00:00'}],[actual])),0)
        self.assertEqual(len(pairs([base],[{**actual,'away':'C'}])),0)

if __name__=='__main__': unittest.main()
