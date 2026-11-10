import unittest
from tools.ml_challengers import choose_weekly_blend, BLEND_NAMES

class WeeklyPlayerMixTests(unittest.TestCase):
    def rows(self, n, weeks, candidate=90):
        return [{'week':i%weeks+1,'actual':100,'baseline':80,
                 **{name:(candidate if name=='baseline_ridge_50' else 80) for name in BLEND_NAMES}} for i in range(n)]
    def test_baseline_when_evidence_too_small(self):
        self.assertEqual(choose_weekly_blend(self.rows(99,3)),'baseline')
        self.assertEqual(choose_weekly_blend(self.rows(150,2)),'baseline')
    def test_selects_better_mix_from_earlier_weeks(self):
        self.assertEqual(choose_weekly_blend(self.rows(150,3)),'baseline_ridge_50')
    def test_retains_baseline_without_meaningful_improvement(self):
        self.assertEqual(choose_weekly_blend(self.rows(150,3,80.1)),'baseline')

if __name__=='__main__': unittest.main()

class FeatureIsolationTests(unittest.TestCase):
    def test_model_features_exclude_target_actual(self):
        import csv
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from tools.ml_challengers import load
        data={'season':2026,'week':4,'player_id':'p','market':'passing_yards',
              'actual':100,'new':150,'old':140,'prior_games':3,'recent_volume':30,
              'recent_yards':160,'team_volume':35,'opponent_ratio':1.1}
        with TemporaryDirectory() as d:
            p=Path(d)/'data.csv'
            def write():
                with p.open('w',newline='') as f:
                    w=csv.DictWriter(f,fieldnames=data.keys());w.writeheader();w.writerow(data)
            write(); before=load(p)[0]['features']; data['actual']=400;write();after=load(p)[0]['features']
            self.assertEqual(before,after)
            self.assertEqual(len(before),8)
