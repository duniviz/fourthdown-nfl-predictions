import unittest
from datetime import datetime, timedelta, timezone
from scripts.freeze_weekly_shadow_models import build
from scripts.freeze_game_ml_predictions import train

class ChallengerTimingTests(unittest.TestCase):
    def test_player_variants_record_actual_freeze_time(self):
        now=datetime(2026,11,8,17,0,tzinfo=timezone.utc)
        kick=now+timedelta(hours=1)
        source={'generated_at_utc':(now-timedelta(hours=2)).isoformat(),'players':[{
            'game_id':'g','player_id':'p','market_key':'player_receptions','base_projection':4,
            'defense_factor':1,'workload_factor':1,'recent_5_avg':4}]}
        snap={'game_id':'g','player_id':'p','market':'player_receptions','projection':4,
              'kickoff':kick.isoformat(),'captured_at':source['generated_at_utc'],'dk_line':3.5}
        rows=build(source,[snap],[],now)
        self.assertTrue(rows)
        self.assertTrue(all(r['predicted_at_utc']==now.isoformat() for r in rows))
        self.assertTrue(all(r['source_forecast_at_utc']==source['generated_at_utc'] for r in rows))
        self.assertEqual(build(source,[snap],[],kick),[])

    def test_same_week_results_are_never_in_prior_features(self):
        games=[]
        for week in range(1,10):
            games.append({'season':2026,'week':week,'home_team':'A','away_team':'B',
                          'home_score':20+week,'away_score':10+week,'game_type':'REG'})
        history,models=train(games,2026,9)
        from scripts.freeze_game_ml_predictions import features
        before=features(history,2026,9,'A','B')
        games[-1]['home_score']=500
        history2,models2=train(games,2026,9)
        self.assertEqual(before,features(history2,2026,9,'A','B'))

if __name__=='__main__':unittest.main()
