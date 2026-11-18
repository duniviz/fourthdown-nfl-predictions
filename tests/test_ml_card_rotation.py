import json, tempfile, unittest, types, sys
import numpy as np
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
from tools import ml_card_rotation as rot

class WeeklySelectionTests(unittest.TestCase):
    def rows(self):
        rows=[];actual={}
        for i in range(12):
            gid=f'2026_10_A{i}_B{i}';key=(gid,'p','passing_yards')
            rows.append({'game_id':gid,'player_id':'p','market':'passing_yards','model_version':'same-refresh-v1',
               'generated_at_utc':'2026-11-08T17:00:00+00:00','kickoff_utc':'2026-11-08T18:00:00+00:00',
               'predictions':{'ridge':110,'random_forest':100,'gradient_boosting':120,'xgboost':130,'current':115}})
            actual[key]=100
        return rows,actual
    def test_latest_week_chooses_same_rows_and_drops_duplicate(self):
        rows,actual=self.rows(); result=rot.select(rows,actual,(2026,11))['passing_yards']
        self.assertEqual(result['model'],'random_forest');self.assertEqual(result['samples'],12)
        result=rot.select(rows+[rows[0]],actual,(2026,11))['passing_yards']
        self.assertEqual(result['samples'],11)
    def test_existing_card_is_retained_when_it_wins(self):
        rows,actual=self.rows()
        for row in rows:row['predictions']['current']=100
        self.assertEqual(rot.select(rows,actual,(2026,11))['passing_yards']['model'],'current')
    def test_missing_model_or_late_capture_never_selects(self):
        rows,actual=self.rows()
        for r in rows:r['predictions'].pop('xgboost')
        self.assertEqual(rot.select(rows,actual,(2026,11)),{})
        rows,actual=self.rows()
        for r in rows:r['generated_at_utc']='2026-11-08T17:46:00+00:00'
        self.assertEqual(rot.select(rows,actual,(2026,11)),{})
    def test_same_or_future_week_cannot_train_selection(self):
        rows,actual=self.rows();self.assertEqual(rot.select(rows,actual,(2026,10)),{})
    def test_conflicting_actual_is_excluded(self):
        key=('2026_10_A_B','p','passing_yards')
        result=rot.actuals([{'game_id':key[0],'player_id':'p','stat_key':key[2],'actual':1},
                            {'game_id':key[0],'player_id':'p','stat_key':key[2],'actual':2}],[])
        self.assertNotIn(key,result)
    def test_full_batch_switches_after_matched_week_and_freezes(self):
        class Model:
            def __init__(self, v):self.v=v
            def predict(self, x):return np.array([self.v for _ in x])
        previous,actual=self.rows()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'backtests').mkdir()
            (root/'backtests/player-predictions.csv').write_text('season,week,market,new,old,actual\n')
            def put(name,obj):(root/name).write_text(json.dumps(obj))
            put('ml-card-batches.json',{'rows':previous})
            put('player-results.json',{'rows':[{'game_id':k[0],'player_id':k[1],'stat_key':k[2],'actual':v} for k,v in actual.items()]})
            put('game-official-results.json',{'rows':[]})
            put('weekly-shadow-forecasts.json',{'rows':[]})
            kick='2026-11-20T18:00:00+00:00';gid='2026_11_A_B'
            put('live-v2.json',{'season':2026,'week':11,'generated_at_utc':'2026-11-18T10:00:00+00:00','games':[{'game_id':gid,'kickoff_utc':kick,'game_ml_shadow':{'markets':{'game_total':{'candidate':40},'game_margin_home':{'candidate':4}}}}]})
            put('player-research.json',{'season':2026,'week':11,'generated_at_utc':'2026-11-18T10:00:00+00:00','players':[{'game_id':gid,'player_id':'new','stat_key':'passing_yards','projection':200,'player_ml_shadow':{'candidate':205}}]})
            put('count-projections.json',{'season':2026,'week':11,'generated_at_utc':'2026-11-18T10:00:00+00:00','players':[]})
            models={n:Model(200+i) for i,n in enumerate(rot.NAMES)}
            game_models={m:{'ml_'+n:Model(30+i) for i,n in enumerate(rot.NAMES)} for m in rot.GAME}
            nfl=types.SimpleNamespace(load_schedules=lambda years:types.SimpleNamespace(to_dicts=lambda:[]))
            with patch.object(rot,'DATA',root),patch.object(rot,'train_games',return_value=({},game_models)),patch.object(rot,'train_yards',return_value={'passing_yards':models}),patch.object(rot,'count_models',return_value={}),patch.object(rot,'game_features',return_value=[1,2,3,4,11]),patch.dict(sys.modules,{'nflreadpy':nfl}):
                rot.run(datetime(2026,11,18,11,tzinfo=timezone.utc))
                report=json.loads((root/'ml-card-rotation.json').read_text())
                self.assertEqual(report['decisions']['passing_yards']['model'],'random_forest')
                row=next(r for r in report['candidates'] if r['player_id']=='new')
                self.assertEqual(row['predictions']['random_forest'],201)
                self.assertEqual(row['predictions']['current'],205)
                first=json.loads((root/'ml-card-batches.json').read_text())
                frozen=next(r for r in first['rows'] if r['player_id']=='new')
                rot.run(datetime(2026,11,20,17,50,tzinfo=timezone.utc))
                after=json.loads((root/'ml-card-batches.json').read_text())
                self.assertEqual(next(r for r in after['rows'] if r['player_id']=='new'),frozen)
                display=json.loads((root/'ml-card-rotation.json').read_text())['candidates']
                self.assertEqual(next(r for r in display if r['player_id']=='new'),frozen)

    def test_predict_rejects_missing_or_nonfinite_models(self):
        self.assertIsNone(rot.predict({},[1,2]))
if __name__=='__main__':unittest.main()
