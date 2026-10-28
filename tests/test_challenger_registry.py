import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from challenger_registry import registry
class RegistryTests(unittest.TestCase):
 def test_all_requested_signals_are_retained(self):
  r=registry([])
  self.assertFalse(r["production_changed"])
  self.assertFalse(r["automatic_promotion"])
  self.assertIn("wopr",r["markets"]["receiving_yards"]["challengers"])
  self.assertIn("proe",r["markets"]["passing_yards"]["challengers"])
  self.assertIn("expected_touchdowns",r["markets"]["touchdowns"]["challengers"])
  self.assertTrue(all(not v["eligible_for_promotion"] for m in r["markets"].values() for v in m["challengers"].values()))
if __name__=="__main__":unittest.main()
