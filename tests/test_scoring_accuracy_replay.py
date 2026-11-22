import copy
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('replay',Path(__file__).resolve().parents[1]/'research/scoring_accuracy_replay.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ReplayTest(unittest.TestCase):
    def fixtures(self):
        games=[]; teams=[]; weekly=[]
        for week in range(1,9):
            gid=f'2024_{week:02d}_A_B'
            games.append(dict(game_id=gid,season=2024,week=week,game_type='REG',home_team='A',away_team='B',home_score=20+week,away_score=17,spread_line=-3,total_line=41))
            for team,epa in [('A',.1),('B',-.1)]:
                teams.append(dict(season=2024,week=week,game_id=gid,team=team,offense_epa=epa,defense_epa=-epa))
                weekly.append(dict(season=2024,week=week,team=team,plays=60,pass_rate=.5,pass_off=epa,rush_off=epa,pass_def=-epa,rush_def=-epa))
        return games,teams,weekly
    def test_future_data_does_not_change_previous_predictions(self):
        games, teams, weekly=self.fixtures()
        original=module.replay(games,teams,weekly)
        changed=copy.deepcopy((games,teams,weekly))
        for row in changed[0]:
            if row['week']>=6: row['home_score']=90
        for row in changed[1]:
            if row['week']>=6: row['offense_epa']=10
        for row in changed[2]:
            if row['week']>=6: row['pass_off']=10
        revised=module.replay(*changed)
        for a,b in zip(original,revised):
            if a['week']<=6:
                self.assertEqual(a['basic'],b['basic'])
                self.assertEqual(a['expanded'],b['expanded'])
                self.assertEqual(a['predictions'],b['predictions'])
    def test_dk_is_not_in_features(self):
        games,teams,weekly=self.fixtures()
        first=module.replay(games,teams,weekly)
        for game in games: game['spread_line']=99;game['total_line']=99
        second=module.replay(games,teams,weekly)
        self.assertEqual([x['expanded'] for x in first],[x['expanded'] for x in second])
        self.assertEqual([x['predictions'] for x in first],[x['predictions'] for x in second])
    def test_metrics(self):
        self.assertEqual(module.metrics([(3,1),(1,3)]),{'samples':2,'mae':2.0,'rmse':2.0,'bias':0.0})
    def test_fitted_model_excludes_target_week_outcome(self):
        games=[]; teams=[]; weekly=[]
        for season in range(2000,2040):
            g,t,w=self.fixtures()
            for row in g+t+w:
                row['season']=season
                if 'game_id' in row: row['game_id']=str(season)+row['game_id'][4:]
            games+=g; teams+=t; weekly+=w
        before=module.replay(games,teams,weekly)
        target=next(r for r in before if 'ridge_expanded' in r['predictions'])
        target_game=next(g for g in games if g['game_id']==target['game_id'])
        target_game['home_score']=99
        after=next(r for r in module.replay(games,teams,weekly) if r['game_id']==target['game_id'])
        self.assertEqual(target['predictions']['ridge_expanded'],after['predictions']['ridge_expanded'])

if __name__=='__main__': unittest.main()
