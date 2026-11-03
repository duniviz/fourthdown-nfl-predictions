import unittest
from live.weekly_learning import evaluate

class WeeklyLearningTests(unittest.TestCase):
    def test_does_not_learn_from_target_week(self):
        archive=[{'game_id':f'2026_{i:02d}_A_B','season':2026,'week':i,
                  'projected_margin_home':0,'projected_total':40} for i in range(1,9)]
        schedules=[{'game_id':r['game_id'],'home_score':30,'away_score':20} for r in archive]
        a=evaluate(archive,schedules,2026,8)
        b=evaluate(archive,schedules,2026,9)
        self.assertEqual(a['margin']['adjustment'],0)
        self.assertEqual(b['margin']['adjustment'],0)
        self.assertEqual(a['margin']['walkforward_games'],0)
    def test_no_promotion_with_insufficient_data(self):
        self.assertFalse(evaluate([],[],2026,8)['total']['enabled'])
    def test_only_completed_games(self):
        archive=[{'game_id':'g','season':2026,'week':1,'projected_margin_home':0,'projected_total':40}]
        schedules=[{'game_id':'g','home_score':None,'away_score':20}]
        self.assertEqual(evaluate(archive,schedules,2026,2)['margin']['walkforward_games'],0)

if __name__=='__main__':unittest.main()
