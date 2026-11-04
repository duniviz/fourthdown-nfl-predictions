import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from freeze_count_ml_predictions import MAP,finite,stamp
class CountMLSafety(unittest.TestCase):
 def test_markets(self):
  self.assertEqual(MAP["player_pass_completions"],"completions")
  self.assertEqual(MAP["player_rush_attempts"],"carries")
  self.assertEqual(MAP["player_receptions"],"receptions")
 def test_bad_data(self):
  self.assertIsNone(finite("nan"))
  self.assertIsNone(finite(None))
  self.assertIsNone(stamp("not-a-timestamp"))
if __name__=="__main__":unittest.main()
