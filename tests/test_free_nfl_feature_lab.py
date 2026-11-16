import unittest
from research.free_nfl_feature_lab import assemble_index,enriched_rows,lagged_values,assess

class FreeFeatureLabTests(unittest.TestCase):
 def test_prior_week_only_and_missing_flags(self):
  series={('receiving','p1'):[((2026,8),[3.0,None,10.0]),((2026,9),[5.0,4.0,12.0]),((2026,10),[99.0,99.0,99.0])]}
  vals,seen=lagged_values(series,'receiving','p1',(2026,10),3)
  self.assertEqual(vals,[4.0,4.0,11.0])
  self.assertEqual(seen,1.)
  vals,seen=lagged_values(series,'receiving','other',(2026,10),3)
  self.assertEqual(vals,[0.0,0.0,0.0])
  self.assertEqual(seen,0.)
 def test_no_target_week_stats_in_training_features(self):
  baseline=[{'season':'2026','week':'10','market':'receiving_yards','player_id':'p1',
   'new':'51','old':'50','prior_games':'8','recent_volume':'7','recent_yards':'60',
   'team_volume':'25','opponent_ratio':'1.2','actual':'62'}]
  source={('receiving','p1'):[((2026,9),[5.,4.,12.]),((2026,10),[999.,999.,999.])]}
  rows=enriched_rows(baseline,source,{})
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]['ngs'],[5.,4.,12.,1.])
  self.assertEqual(rows[0]['snap'][-1],0.)
  self.assertEqual(rows[0]['pfr'][-1],0.)
  self.assertEqual(rows[0]['baseline'],51.)
 def test_duplicate_source_rows_do_not_count_as_independent(self):
  sources={'ngs_receiving_2026':[
   {'season':2026,'week':9,'season_type':'REG','player_gsis_id':'p1','avg_separation':1},
   {'season':2026,'week':9,'season_type':'REG','player_gsis_id':'p1','avg_separation':5}]}
  index,mapping,coverage=assemble_index(sources)
  self.assertEqual(index[('receiving','p1')],[])
  self.assertEqual(coverage['ngs_receiving_2026']['eligible_rows'],2)
 def test_insufficient_heldout_data_does_not_qualify(self):
  result=assess([])
  self.assertEqual(result['receiving_yards']['holdout_rows'],0)
  self.assertEqual(result['receiving_yards']['models'],{})
if __name__=='__main__':unittest.main()
