import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from multiseason_passing_championship import compare
class ChampionshipTests(unittest.TestCase):
 def rows(self,season):
  return [{"season":str(season),"week":str(w),"season_type":"REG","player_id":pid,"player_name":pid,"recent_team":team,"opponent_team":opp,"passing_yards":str(160+w*4),"attempts":"30"}
    for w in range(1,11) for pid,team,opp in (("a","AAA","BBB"),("b","BBB","AAA"))]
 def test_three_seasons(self):
  r=compare({2024:self.rows(2024),2025:self.rows(2025),2026:self.rows(2026)},4)
  self.assertEqual(len(r["seasons"]),3)
  self.assertFalse(r["production_change_approved"])
  self.assertEqual(r["pooled_holdout"]["baseline"]["samples"],24)
 def test_insufficient_season(self):
  r=compare({2024:self.rows(2024)[:6]},4)
  self.assertEqual(r["seasons"]["2024"]["status"],"insufficient_history")
  self.assertEqual(r["consistent_candidates"],[])
 def test_independent_year(self):
  a=compare({2024:self.rows(2024),2025:self.rows(2025)},4)
  b=compare({2024:self.rows(2024),2025:self.rows(2025),2026:self.rows(2026)},4)
  self.assertEqual(a["seasons"]["2024"],b["seasons"]["2024"])
if __name__=="__main__":unittest.main()
