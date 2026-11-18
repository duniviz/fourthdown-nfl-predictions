import csv,gzip,json,tempfile,unittest,types,sys
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from tools.export_ml_card_history import export
from tools import ml_card_rotation as rot
from tools import evaluate_ml_card_history as evaluation
import numpy as np

class ExpandedHistoryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  (self.root/'backtests').mkdir()
  (self.root/'backtests/player-predictions.csv').write_text('season,week,market,player_id,new,old,actual\n2025,1,passing_yards,p,1,1,1\n')
 def tearDown(self):self.temp.cleanup()
 def source(self):
  path=self.root/'input.csv'
  with path.open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=['season','week','player_id','market','new','old','actual','prior_games','recent_volume','recent_yards']);w.writeheader()
   for m in sorted(rot.YARDS):
    for i in range(100):w.writerow({'season':2016,'week':4+i%14,'player_id':f'p{i}','market':m,'new':10,'old':10,'actual':12,'prior_games':4,'recent_volume':8,'recent_yards':12})
    w.writerow({'season':2026,'week':10,'player_id':'recent','market':m,'new':10,'old':10,'actual':12,'prior_games':4,'recent_volume':8,'recent_yards':12})
    w.writerow({'season':2026,'week':11,'player_id':'target','market':m,'new':10,'old':10,'actual':12,'prior_games':4,'recent_volume':8,'recent_yards':12})
   duplicate={'season':2016,'week':4,'player_id':'duplicate','market':'passing_yards','new':5,'old':5,'actual':6,'prior_games':4,'recent_volume':8,'recent_yards':6}
   w.writerow(duplicate);w.writerow(duplicate)
  return path
 def test_extended_data_excludes_ambiguous_and_target_week(self):
  report=export(self.source(),self.root/'ml-card-training.csv.gz',self.root/'ml-card-training-meta.json')
  self.assertEqual(report['ambiguous_identities_excluded'],1)
  with patch.object(rot,'DATA',self.root):rows,version,coverage=rot.load_yard_training((2026,11))
  self.assertEqual(version,'same-refresh-v2');self.assertEqual(coverage['latest_training_week'],10)
  self.assertEqual(set(coverage['seasons']),{2016,2026})
  self.assertFalse(any(r['player_id'] in ('duplicate','target') for r in rows))
 def test_corrupt_or_stale_archive_uses_existing_fallback(self):
  export(self.source(),self.root/'ml-card-training.csv.gz',self.root/'ml-card-training-meta.json')
  with patch.object(rot,'DATA',self.root):
   _,version,_=rot.load_yard_training((2026,14))
  self.assertEqual(version,'same-refresh-v1')
  with (self.root/'ml-card-training.csv.gz').open('ab') as f:f.write(b'tampered')
  with patch.object(rot,'DATA',self.root):
   _,version,_=rot.load_yard_training((2026,11))
  self.assertEqual(version,'same-refresh-v1')
 def test_expanded_models_are_not_mixed_with_old_version(self):
  row={'game_id':'2026_10_A_B','player_id':'p','market':'passing_yards','model_version':'same-refresh-v1',
       'generated_at_utc':'2026-11-08T17:00:00+00:00','kickoff_utc':'2026-11-08T18:00:00+00:00',
       'predictions':{k:10 for k in (*rot.NAMES,'current')}}
  rows=[];actual={}
  for i in range(10):
   r={**row,'game_id':f'2026_10_A{i}_B{i}'};rows.append(r);actual[(r['game_id'],'p','passing_yards')]=11
  self.assertEqual(rot.select(rows,actual,(2026,11),{'passing_yards':'same-refresh-v2'}),{})
  self.assertIn('passing_yards',rot.select(rows,actual,(2026,11),{'passing_yards':'same-refresh-v1'}))
 def test_live_form_uses_only_prior_player_inputs(self):
  p={'projection':50,'last_5':[10,20,30,40,50],'games_used':5,'last_5_opportunities_avg':8}
  v=rot.live_form(p,11)
  self.assertEqual(v,[50.0,.55*40+.45*30,5.0,8.0,30.0,11.0])
  p['games_used']=2
  self.assertIsNone(rot.live_form(p,11))
 def test_form_model_ignores_target_week_results(self):
  rows=[]
  for i in range(110):
   rows.append({'season':'2025','week':str(1+i%17),'market':'passing_yards',
    'new':str(180+i%30),'old':str(175+i%30),'actual':str(190+i%30),
    'prior_games':'5','recent_volume':'20','recent_yards':str(190+i%30)})
  future={'season':'2026','week':'11','market':'passing_yards','new':'200','old':'200','actual':'9999',
    'prior_games':'9','recent_volume':'30','recent_yards':'200'}
  before=rot.train_yard_form(rows,(2026,11))['passing_yards']
  after=rot.train_yard_form(rows+[future],(2026,11))['passing_yards']
  features=[[200,195,5,20,190,11]]
  for name in rot.NAMES:self.assertAlmostEqual(float(before[name].predict(features)[0]),float(after[name].predict(features)[0]),places=6)
 def test_batched_predictions_match_individual_predictions(self):
  class Model:
   def predict(self,x):return np.asarray(x,dtype=float)[:,0]+3
  models={name:Model() for name in rot.NAMES};vectors=[[1,2],[4,5],[9,10]]
  batch=rot.predict_batch(models,vectors)
  for i,vector in enumerate(vectors):
   individual=rot.predict(models,vector)
   for name in rot.NAMES:self.assertEqual(float(batch[name][i]),individual[name])
 def test_expanded_batch_publishes_selected_form_candidate(self):
  class Model:
   def __init__(self,v):self.v=v
   def predict(self,x):return np.ones(len(x))*self.v
  models={n:Model(100+i) for i,n in enumerate(rot.NAMES)}
  def put(name,data):(self.root/name).write_text(json.dumps(data))
  previous=[];results=[]
  for i in range(10):
   gid=f'2026_10_A{i}_B{i}';pred={n:20 for n in (*rot.YARD_NAMES,'current')};pred['xgboost_form_recent']=10
   previous.append({'game_id':gid,'player_id':'p','market':'passing_yards','model_version':'same-refresh-v2','generated_at_utc':'2026-11-08T17:00:00+00:00','kickoff_utc':'2026-11-08T18:00:00+00:00','predictions':pred})
   results.append({'game_id':gid,'player_id':'p','stat_key':'passing_yards','actual':10})
  put('ml-card-batches.json',{'rows':previous});put('player-results.json',{'rows':results});put('game-official-results.json',{'rows':[]});put('weekly-shadow-forecasts.json',{'rows':[]})
  gid='2026_11_A_B';put('live-v2.json',{'season':2026,'week':11,'generated_at_utc':'2026-11-18T10:00:00+00:00','games':[{'game_id':gid,'kickoff_utc':'2026-11-20T18:00:00+00:00'}]})
  put('player-research.json',{'season':2026,'week':11,'generated_at_utc':'2026-11-18T10:00:00+00:00','players':[{'game_id':gid,'player_id':'p2','stat_key':'passing_yards','projection':200,'last_5':[100,110,120],'games_used':3,'last_5_opportunities_avg':20,'player_ml_shadow':{'candidate':205}}]})
  put('count-projections.json',{'season':2026,'week':11,'generated_at_utc':'2026-11-18T10:00:00+00:00','players':[]})
  nfl=types.SimpleNamespace(load_schedules=lambda years:types.SimpleNamespace(to_dicts=lambda:[]))
  rows=[{'season':'2025'}]
  with patch.object(rot,'DATA',self.root),patch.object(rot,'load_yard_training',return_value=(rows,'same-refresh-v2',{'archive_sha256':'test'})),patch.object(rot,'train_games',return_value=({},{})),patch.object(rot,'game_features',return_value=None),patch.object(rot,'train_yards',side_effect=lambda rows,target:{'passing_yards':dict(models)}),patch.object(rot,'train_yard_form',side_effect=lambda rows,target:{'passing_yards':dict(models)}),patch.object(rot,'count_models',return_value={}),patch.dict(sys.modules,{'nflreadpy':nfl}):
   rot.run(datetime(2026,11,18,11,tzinfo=timezone.utc))
   saved=json.loads((self.root/'ml-card-batches.json').read_text());prior=next(r for r in saved['rows'] if r['player_id']=='p2');prior['model_version']='same-refresh-v1';prior['selected']={'model':'ridge','week':10,'samples':10};(self.root/'ml-card-batches.json').write_text(json.dumps(saved))
   rot.run(datetime(2026,11,20,17,50,tzinfo=timezone.utc))
   frozen=json.loads((self.root/'ml-card-rotation.json').read_text())['candidates'][0]
   self.assertEqual(frozen['model_version'],'same-refresh-v1');self.assertEqual(frozen['selected']['model'],'ridge')
   rot.run(datetime(2026,11,18,11,tzinfo=timezone.utc))
  report=json.loads((self.root/'ml-card-rotation.json').read_text());candidate=report['candidates'][0]
  self.assertEqual(report['decisions']['passing_yards']['model'],'xgboost_form_recent')
  self.assertEqual(candidate['selected']['model'],'xgboost_form_recent');self.assertEqual(len(candidate['predictions']),17)
  self.assertEqual(candidate['training_archive_sha256'],'test')
 def test_history_export_failure_preserves_existing_archive(self):
  output=self.root/'ml-card-training.csv.gz';meta=self.root/'ml-card-training-meta.json'
  output.write_bytes(b'existing');meta.write_text('existing')
  path=self.root/'empty.csv';path.write_text('season,week,player_id,market,new,old,actual,prior_games,recent_volume,recent_yards\n')
  with self.assertRaises(ValueError):export(path,output,meta)
  self.assertEqual(output.read_bytes(),b'existing');self.assertEqual(meta.read_text(),'existing')
 def test_historical_evaluation_trains_only_before_holdout(self):
  class Model:
   def predict(self,x):return np.ones(len(x))*10
  models={n:Model() for n in rot.NAMES};calls=[]
  def fit(rows,target):
   calls.append((target,{int(r['season']) for r in rows}))
   return {'passing_yards':models}
  rows=[]
  for season in (2024,2025,2026):
   for i in range(40):rows.append({'season':str(season),'week':str(1+i%10),'market':'passing_yards','new':'10','old':'9','actual':'12','prior_games':'4','recent_volume':'8','recent_yards':'10'})
  rows.append({**rows[-1],'season':'2026','week':'11','actual':'9999'})
  with patch.object(evaluation,'fit',side_effect=fit),patch.object(evaluation,'train_yard_form',side_effect=fit):result=evaluation.evaluate(rows,(2026,11))
  self.assertEqual([r['holdout_season'] for r in result['results']],[2025,2026])
  self.assertTrue(all(all(y<target[0] for y in years) for target,years in calls))
  self.assertEqual(result['results'][-1]['samples'],40)
 def test_latest_week_required_for_rotation(self):
  rows=[];actual={}
  for i in range(10):
   gid=f'2026_09_A{i}_B{i}';rows.append({'game_id':gid,'player_id':'p','market':'passing_yards','model_version':'same-refresh-v1',
    'generated_at_utc':'2026-11-01T17:00:00+00:00','kickoff_utc':'2026-11-01T18:00:00+00:00','predictions':{k:10 for k in (*rot.NAMES,'current')}});actual[(gid,'p','passing_yards')]=10
  self.assertEqual(rot.select(rows,actual,(2026,11)),{})
 def test_recent_window_competes_on_same_expanded_rows(self):
  rows=[];actual={}
  for i in range(10):
   gid=f'2026_10_A{i}_B{i}';pred={k:20 for k in (*rot.YARD_NAMES,'current')};pred['xgboost_recent']=10
   rows.append({'game_id':gid,'player_id':'p','market':'passing_yards','model_version':'same-refresh-v2',
    'generated_at_utc':'2026-11-08T17:00:00+00:00','kickoff_utc':'2026-11-08T18:00:00+00:00','predictions':pred});actual[(gid,'p','passing_yards')]=10
  self.assertEqual(rot.select(rows,actual,(2026,11),{'passing_yards':'same-refresh-v2'})['passing_yards']['model'],'xgboost_recent')
  del rows[0]['predictions']['ridge_recent']
  self.assertEqual(rot.select(rows,actual,(2026,11),{'passing_yards':'same-refresh-v2'}),{})
if __name__=='__main__':unittest.main()
