import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from three_factor_prop_lab import evaluate
class ThreeFactorTests(unittest.TestCase):
 def fixtures(self):
  rows=[];games=[]
  for week in range(1,15):
   for home,away in (("AAA","BBB"),("CCC","DDD")):
    games.append({"season":"2025","week":str(week),"game_type":"REG","home_team":home,"away_team":away,"home_score":str(20+week%6),"away_score":str(16+week%4)})
   for team in ("AAA","BBB","CCC","DDD"):
    rows.append({"season":"2025","week":str(week),"season_type":"REG","player_id":"qb"+team,"recent_team":team,"passing_yards":str(210+week),"attempts":"30","receiving_yards":"0","targets":"0","rushing_yards":"0","carries":"0"})
    rows.append({"season":"2025","week":str(week),"season_type":"REG","player_id":"wr"+team,"recent_team":team,"passing_yards":"0","attempts":"0","receiving_yards":str(60+week),"targets":"8","rushing_yards":"0","carries":"0"})
  return rows,games
 def test_all_three_factors_and_holdout(self):
  rows,games=self.fixtures();out=evaluate(rows,games,2025)
  self.assertEqual(out["status"],"research_only")
  self.assertFalse(out["production_change_approved"])
  self.assertGreater(out["results"]["holdout"]["qb_attempts_efficiency"]["passing_yards"]["samples"],0)
  self.assertGreater(out["results"]["holdout"]["receiver_target_share"]["receiving_yards"]["samples"],0)
  self.assertGreater(out["results"]["holdout"]["pregame_game_script"]["passing_yards"]["samples"],0)
 def test_future_results_cannot_affect_earlier_predictions(self):
  rows,games=self.fixtures()
  rows=[r for r in rows if int(r["week"])<=10];games=[g for g in games if int(g["week"])<=10]
  a=evaluate(rows,games,2025)
  changed=[dict(g) for g in games]
  for g in changed:
   if int(g["week"])==10:g["home_score"]="90"
  b=evaluate(rows,changed,2025)
  # Week 10 observations affect grades, but never prior week predictions.
  self.assertEqual(a["results"]["development"],b["results"]["development"])
 def test_insufficient_history(self):
  self.assertEqual(evaluate([],[],2025)["status"],"insufficient_completed_weeks")
if __name__=="__main__":unittest.main()
