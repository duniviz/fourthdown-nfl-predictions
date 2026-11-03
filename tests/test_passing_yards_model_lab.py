import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from passing_yards_model_lab import evaluate,metrics,VARIANTS
class PassingLabTests(unittest.TestCase):
 def data(self,late=0):
  rows=[]
  for week in range(1,9):
   for pid,team,opponent in (("qb1","AAA","BBB"),("qb2","BBB","AAA")):
    rows.append({"season":"2026","week":str(week),"season_type":"REG","player_id":pid,"player_name":pid,"recent_team":team,"opponent_team":opponent,"passing_yards":str(180+week*10+(late if week==8 else 0)),"attempts":"30","team_score":"24","opponent_score":"21"})
  return rows
 def test_future_week_cannot_change_prior_results(self):
  a=evaluate(self.data(),2026,7,2)
  b=evaluate(self.data(400),2026,7,2)
  self.assertEqual(a["results"],b["results"])
 def test_holdout_is_later_weeks(self):
  r=evaluate(self.data(),2026,8,2)
  self.assertEqual(r["holdout_weeks"],[7,8])
  self.assertEqual(r["results"]["holdout"]["baseline"]["samples"],4)
  self.assertFalse(r["production_change_approved"])
 def test_all_variants(self):
  r=evaluate(self.data(),2026,8,2)
  self.assertEqual(set(r["results"]["holdout"]),set(VARIANTS))
 def test_empty_metrics(self):self.assertIsNone(metrics([])["mae"])
if __name__=="__main__":unittest.main()
