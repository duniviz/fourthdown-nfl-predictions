import copy
import unittest
from collections import defaultdict
from research.player_opportunity_features import add_weekly_features
from research.free_nfl_feature_lab import lagged_values
from research.publish_advanced_player_ml import features_for_player, build_source_features
from research.select_market_ml import choose_player
from live.advanced_player_ml import candidate, FAMILY


class PlayerOpportunityTests(unittest.TestCase):
    def test_completed_games_and_prior_week_only(self):
        base={'season':2026,'season_type':'REG','team':'A','opponent_team':'B',
              'player_id':'p','targets':4,'target_share':.25,'air_yards_share':.4,
              'receiving_air_yards':40,'carries':5,'rushing_yards':25,
              'rushing_epa':2,'receiving_yards':35,'receiving_epa':3}
        old={**base,'week':1,'game_id':'old'}
        future={**base,'week':2,'game_id':'future','receiving_air_yards':400,'receiving_yards':999}
        series=defaultdict(list)
        add_weekly_features(series,[old,future],{'old','future'})
        v=features_for_player(series,{},'p','receiving_yards',(2026,2),'B')
        self.assertEqual(v['workload'],[.25,.4,10.,1.])
        self.assertEqual(v['matchup'][0],8.75)
        self.assertEqual(lagged_values(series,'workload_receiving_yards','p',(2026,1),3)[1],0)
        filtered=defaultdict(list)
        add_weekly_features(filtered,[old,future],{'old'})
        self.assertEqual(len(filtered[('workload_receiving_yards','p')]),1)
        duplicate=defaultdict(list)
        add_weekly_features(duplicate,[old,dict(old)],{'old'})
        self.assertNotIn(('workload_receiving_yards','p'),duplicate)

    def test_opponent_identity_and_missing_inputs_fall_back(self):
        model={'variant':'opponent_efficiency','feature_groups':['matchup'],
               'coefficients':[0.]*12,'intercept':50.,'active':False,
               'trained_season':2026,'trained_week':9}
        runtime={'family':FAMILY,'target_season':2026,'target_week':10,
                 'generated_at_utc':'t','models':{'receiving_yards':model}}
        players={'p':{'receiving_yards':{'opponent':'B','matchup':[7.,1.,.1,1.]}}}
        feats={'family':FAMILY,'target_season':2026,'target_week':10,
               'generated_at_utc':'t','players':players}
        args=(runtime,feats,'receiving_yards','p',2026,10,50.,50.,5.,5.,50.,30.,1.)
        self.assertIsNotNone(candidate(*args,opponent='B'))
        self.assertIsNone(candidate(*args,opponent='C'))
        players['p']['receiving_yards']['matchup'][-1]=0.
        self.assertIsNone(candidate(*args,opponent='B'))

    def test_ambiguous_opponent_is_not_accepted(self):
        rows=[{'player_id':'p','stat_key':'receiving_yards','opponent':'A'},
              {'player_id':'p','stat_key':'receiving_yards','opponent':'B'}]
        features=build_source_features({}, {}, rows, (2026,10), {'receiving_yards':{}})
        self.assertIsNone(features['p']['receiving_yards'])

    def test_new_features_must_win_independent_matched_confirmation(self):
        legacy={'status':'evaluated','samples':400,'baseline_mae':25.,'challenger_mae':24.,'improvement_pct':4}
        new={'status':'evaluated','samples':400,'baseline_mae':25.,'challenger_mae':23.,'improvement_pct':8}
        comparison={'reference':'baseline_features',
                    'selection':{'samples':200,'weeks':5,'candidate_mae':22.,'reference_mae':24.},
                    'confirmation':{'samples':100,'weeks':4,'candidate_mae':23.,'reference_mae':24.,
                                    'candidate_rmse':29.,'reference_rmse':30.}}
        report={'holdout_rows':400,'holdout_weeks':9,'source_coverage':{},
                'models':{'baseline_features':legacy,'weekly_workload':new},
                'new_feature_comparisons':{'weekly_workload':comparison}}
        self.assertEqual(choose_player('rushing_yards',report)['research_winner'],'weekly_workload')
        fail=copy.deepcopy(report)
        fail['new_feature_comparisons']['weekly_workload']['confirmation']['candidate_mae']=25.
        self.assertEqual(choose_player('rushing_yards',fail)['research_winner'],'baseline_features')
        fail=copy.deepcopy(report)
        fail['new_feature_comparisons']['weekly_workload']['confirmation']['candidate_rmse']=31.
        self.assertEqual(choose_player('rushing_yards',fail)['research_winner'],'baseline_features')


if __name__=='__main__': unittest.main()
