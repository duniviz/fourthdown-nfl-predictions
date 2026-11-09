import unittest
from live.weekly_learning import evaluate

class WeeklyLearningTests(unittest.TestCase):
    def test_does_not_learn_from_target_week(self):
        archive=[{'game_id':f'2026_{i:02d}_A_B','season':2026,'week':i,
                  'kickoff_utc':f'2026-09-{i+1:02d}T18:00:00Z',
                  'published_at_utc':f'2026-09-{i+1:02d}T12:00:00Z',
                  'projected_margin_home':0,'projected_total':40} for i in range(1,9)]
        schedules=[{'game_id':r['game_id'],'home_score':30,'away_score':20} for r in archive]
        a=evaluate(archive,schedules,2026,8)
        b=evaluate(archive,schedules,2026,9)
        self.assertEqual(a['margin']['adjustment'],0)
        self.assertEqual(b['margin']['adjustment'],0)
        self.assertEqual(a['margin']['walkforward_games'],0)
    def test_postkickoff_archives_do_not_train_or_validate(self):
        archive=[]
        for week in range(1,7):
            for game in range(10):
                archive.append({'game_id':f'2026_{week:02d}_A{game}_B', 'season':2026,'week':week,
                    'projected_margin_home':0,'projected_total':40,
                    'published_at_utc':'2026-01-01T16:00:00+00:00','kickoff_utc':'2026-01-01T18:00:00+00:00'})
        schedules=[{'game_id':r['game_id'],'home_score':30,'away_score':20} for r in archive]
        valid=evaluate(archive,schedules,2026,8)
        self.assertGreater(valid['margin']['walkforward_games'],0)
        leaked=[{**r,'published_at_utc':'2026-01-01T19:00:00+00:00'} for r in archive]
        rejected=evaluate(leaked,schedules,2026,8)
        self.assertEqual(rejected['margin']['walkforward_games'],0)
        self.assertFalse(rejected['margin']['enabled'])
    def test_no_promotion_with_insufficient_data(self):
        self.assertFalse(evaluate([],[],2026,8)['total']['enabled'])
    def test_only_completed_games(self):
        archive=[{'game_id':'g','season':2026,'week':1,'kickoff_utc':'2026-09-01T18:00:00Z',
                  'published_at_utc':'2026-09-01T12:00:00Z','projected_margin_home':0,'projected_total':40}]
        schedules=[{'game_id':'g','home_score':None,'away_score':20}]
        self.assertEqual(evaluate(archive,schedules,2026,2)['margin']['walkforward_games'],0)

    def test_requires_timestamped_forecast_before_kickoff(self):
        prior=[{'game_id':f'2026_{i:02d}_A_B','season':2026,'week':i,
                'kickoff_utc':f'2026-09-{i:02d}T18:00:00Z',
                'published_at_utc':f'2026-09-{i:02d}T17:00:00Z',
                'projected_margin_home':0,'projected_total':40} for i in range(1,17)]
        target={'game_id':'2026_17_A_B','season':2026,'week':17,'kickoff_utc':'2026-09-17T18:00:00Z',
                'projected_margin_home':0,'projected_total':40}
        schedules=[{'game_id':r['game_id'],'home_score':30,'away_score':20} for r in prior+[target]]
        missing=evaluate(prior+[target],schedules,2026,18)
        postgame=evaluate(prior+[{**target,'published_at_utc':'2026-09-17T19:00:00Z'}],schedules,2026,18)
        pregame=evaluate(prior+[{**target,'published_at_utc':'2026-09-17T17:00:00Z'}],schedules,2026,18)
        self.assertEqual(missing['margin']['walkforward_games'],0)
        self.assertEqual(postgame['margin']['walkforward_games'],0)
        self.assertEqual(pregame['margin']['walkforward_games'],1)

    def test_verified_game_lock_is_the_learning_record_when_available(self):
        prior=[{'game_id':f'2026_{i:02d}_A_B','season':2026,'week':i,
                'kickoff_utc':f'2026-09-{i:02d}T18:00:00Z',
                'published_at_utc':f'2026-09-{i:02d}T17:00:00Z',
                'projected_margin_home':0,'projected_total':40} for i in range(1,17)]
        gid='2026_17_A_B'
        base={**prior[-1],'game_id':gid,'week':17,'kickoff_utc':'2026-09-17T18:00:00Z',
              'published_at_utc':'2026-09-17T12:00:00Z'}
        schedules=[{'game_id':r['game_id'],'home_score':30,'away_score':20} for r in prior]
        schedules.append({'game_id':gid,'home_score':25,'away_score':20})
        lock={'game_id':gid,'season':2026,'week':17,'kickoff_utc':'2026-09-17T18:00:00Z',
              'forecast_at_utc':'2026-09-17T17:40:00Z','captured_at_utc':'2026-09-17T17:45:00Z',
              'lock_status':'official','projected_margin_home':5,'projected_total':45}
        report=evaluate(prior+[base],schedules,2026,18,[lock])
        self.assertEqual(report['margin']['baseline_mae'],0.0)
        self.assertEqual(report['total']['baseline_mae'],0.0)

if __name__=='__main__':unittest.main()
