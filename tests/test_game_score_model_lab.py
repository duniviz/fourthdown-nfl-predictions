import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from game_score_model_lab import evaluate
class ScoreLabTests(unittest.TestCase):
 def games(self,season=2025):
  return [{"season":str(season),"week":str(w),"game_type":"REG","home_team":h,"away_team":a,"home_score":str(20+w%5),"away_score":str(17+w%3)}
   for w in range(1,15) for h,a in (("AAA","BBB"),("CCC","DDD"),("BBB","CCC"),("DDD","AAA"))]
 def test_research_only_and_metrics(self):
  x=evaluate(self.games(),2025)
  self.assertFalse(x["production_change_approved"])
  self.assertEqual(x["status"],"research_only")
  self.assertGreater(x["results"]["holdout"]["baseline"]["total"]["samples"],0)
  self.assertEqual(x["results"]["holdout"]["baseline"]["total"]["samples"],x["results"]["holdout"]["recent_form"]["total"]["samples"])
 def test_future_results_do_not_change_earlier_holdout(self):
  early=evaluate([x for x in self.games() if int(x["week"])<=10],2025,4)
  later=self.games()
  for row in later:
   if int(row["week"])>10:row["home_score"]="90"
  modified=evaluate([x for x in later if int(x["week"])<=10],2025,4)
  self.assertEqual(early,modified)
 def test_no_games(self):
  self.assertEqual(evaluate([],2025)["status"],"insufficient_completed_weeks")
if __name__=="__main__":unittest.main()
