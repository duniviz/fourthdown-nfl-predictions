import copy
import unittest
from collections import defaultdict
import polars as pl
from research.ftn_player_features import load_joined,add_charted_features
from research.free_nfl_feature_lab import assemble_index,enriched_rows,lagged_values,complete_lagged_values
from research.publish_advanced_player_ml import features_for_player
from research.select_market_ml import choose_player
from live.advanced_player_ml import candidate,FAMILY


class FeatureTests(unittest.TestCase):
 def test_pfr_current_schema_maps_players_without_changing_old_combinations(self):
  data={'players_2026':[{'gsis_id':'g','pfr_id':'p'}],
        'pfr_pass_2026':[{'pfr_player_id':'p','season':2026,'week':9,'times_pressured_pct':.2,
                          'passing_bad_throw_pct':.1,'passing_drop_pct':.05}]}
  index,ids,coverage=assemble_index(data)
  self.assertEqual(coverage['pfr_pass_2026']['eligible_rows'],1)
  f=features_for_player(index,ids,'g','passing_yards',(2026,10),'A')
  self.assertEqual(f['pfr_new'],[.2,.1,.05,1.])
  self.assertEqual(f['pfr'],[0.,0.,0.,0.])
  self.assertEqual(features_for_player(index,ids,'g','passing_yards',(2026,9),'A')['pfr_new'][-1],0.)
  missing={('ftn_passing_yards','g'):[((2026,9),[.1,None,4.])]}
  self.assertEqual(complete_lagged_values(missing,'ftn_passing_yards','g',(2026,10),3),([0.,0.,0.],0.))

 def test_chart_join_rejects_duplicate_and_nonintegral_ids(self):
  pbp=pl.DataFrame({'game_id':['g','g','g'],'play_id':[1.,2.,3.5],'season':[2026]*3,'week':[1]*3,
   'season_type':['REG']*3,'play_type':['pass']*3,'passer_player_id':['p']*3,
   'receiver_player_id':['r']*3,'rusher_player_id':[None]*3,'defteam':['D']*3})
  chart=pl.DataFrame({'nflverse_game_id':['g']*4,'nflverse_play_id':[1,2,2,3],
   'is_play_action':[True]*4,'is_screen_pass':[False]*4,'is_catchable_ball':[True]*4,
   'is_contested_ball':[False]*4,'read_thrown':['0']*4,'n_defense_box':[6]*4,
   'is_motion':[True]*4,'is_rpo':[False]*4,'n_blitzers':[1]*4,'n_pass_rushers':[4]*4})
  class NFL:
   def load_pbp(self,_):return pbp
   def load_ftn_charting(self,_):return chart
  rows=load_joined(NFL(),2026,{'g'})
  self.assertEqual([r['play_id'] for r in rows],[1])
  series=defaultdict(list);add_charted_features(series,rows)
  self.assertEqual(lagged_values(series,'ftn_passing_yards','p',(2026,2),3),([1.,0.,4.],1.))
  self.assertEqual(lagged_values(series,'ftn_passing_yards','p',(2026,1),3)[1],0.)
  self.assertEqual(lagged_values(series,'ftn_defense_passing_yards','D',(2026,2),3)[0],[4.,1.,1.])

 def test_ftn_inference_requires_current_opponent_and_source(self):
  model={'variant':'ftn_opponent','feature_groups':['ftn_defense'],'coefficients':[0.]*12,
         'intercept':50.,'active':False,'trained_season':2026,'trained_week':9}
  runtime={'family':FAMILY,'target_season':2026,'target_week':10,'generated_at_utc':'t','models':{'passing_yards':model}}
  inputs={'opponent':'B','ftn_defense':[4.,1.,.2,1.]}
  features={'family':FAMILY,'target_season':2026,'target_week':10,'generated_at_utc':'t','players':{'p':{'passing_yards':inputs}}}
  args=(runtime,features,'passing_yards','p',2026,10,50.,50.,5.,5.,50.,30.,1.)
  self.assertIsNotNone(candidate(*args,opponent='B'))
  self.assertIsNone(candidate(*args,opponent='C'))
  inputs['ftn_defense'][-1]=0.
  self.assertIsNone(candidate(*args,opponent='B'))

 def test_new_source_must_beat_incumbent_in_confirmation(self):
  base={'status':'evaluated','samples':400,'baseline_mae':25.,'challenger_mae':24.,'improvement_pct':4}
  fresh={'status':'evaluated','samples':400,'baseline_mae':25.,'challenger_mae':23.,'improvement_pct':8}
  cmp={'reference':'advanced_matchup','selection':{'samples':200,'weeks':5,'candidate_mae':22.,'reference_mae':24.},
       'confirmation':{'samples':100,'weeks':4,'candidate_mae':23.,'reference_mae':24.,'candidate_rmse':29.,'reference_rmse':30.}}
  report={'holdout_rows':400,'holdout_weeks':9,'source_coverage':{},'models':{'baseline_features':base,'ftn_player':fresh},'pfr_ftn_comparisons':{'ftn_player':cmp}}
  self.assertEqual(choose_player('passing_yards',report)['research_winner'],'ftn_player')
  fail=copy.deepcopy(report);fail['pfr_ftn_comparisons']['ftn_player']['confirmation']['candidate_rmse']=31.
  self.assertEqual(choose_player('passing_yards',fail)['research_winner'],'baseline_features')
  retained=copy.deepcopy(report);retained['pfr_ftn_incumbent']='ftn_player'
  retained['pfr_ftn_retention']=copy.deepcopy(cmp)
  retained['pfr_ftn_comparisons']={}
  self.assertEqual(choose_player('passing_yards',retained)['research_winner'],'ftn_player')
  retained['pfr_ftn_retention']['confirmation']['candidate_mae']=26.
  self.assertEqual(choose_player('passing_yards',retained)['research_winner'],'baseline_features')

if __name__=='__main__':unittest.main()
