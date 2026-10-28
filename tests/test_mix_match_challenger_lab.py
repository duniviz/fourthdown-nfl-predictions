import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from mix_match_challenger_lab import evaluate
class LabTests(unittest.TestCase):
 def test_insufficient_data_never_promotes(self):
  result=evaluate([],2026)
  self.assertFalse(result["production_changed"])
  self.assertEqual(result["status"],"insufficient_completed_weeks")
if __name__=="__main__":unittest.main()
