import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from nfl_savant_feature_lab import evaluate
class SavantFeatureTests(unittest.TestCase):
 def rows(self):
  out=[]
  for w in range(1,13):
   for team in ("AAA","BBB"):
    for role in ("QB","RB","WR"):
     out.append({"season":"2025","week":str(w),"season_type":"REG","player_id":role+team,"recent_team":team,"attempts":"30" if role=="QB" else "0","passing_yards":str(200+w) if role=="QB" else "0","carries":"15" if role=="RB" else "0","rushing_yards":str(60+w) if role=="RB" else "0","targets":"8" if role=="WR" else "0","receiving_yards":str(70+w) if role=="WR" else "0"})
  return out
 def test_opportunity_features_and_holdout(self):
  result=evaluate(self.rows(),2025)
  self.assertEqual(result["status"],"research_only")
  self.assertFalse(result["production_change_approved"])
  self.assertGreater(result["results"]["holdout"]["passing_yards"]["baseline"]["samples"],0)
  self.assertFalse(result["feature_availability"]["play_by_play"]["air_yards"])
 def test_earlier_predictions_ignore_future(self):
  a=self.rows();b=[dict(r) for r in a]
  for r in b:
   if r["week"]=="12":r["passing_yards"]="600"
  first=evaluate(a,2025);second=evaluate(b,2025)
  self.assertEqual(first["results"]["development"],second["results"]["development"])
 def test_insufficient_history(self):
  self.assertEqual(evaluate([],2025)["status"],"insufficient_completed_weeks")
if __name__=="__main__":unittest.main()
