"""Guard against regressions in pregame DK archive grading keys."""
import unittest
from pathlib import Path

class PregameArchiveGradingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=Path("scripts/capture_pregame_snapshots.py").read_text()
        cls.grader=Path("live/player_results.py").read_text()
    def test_capture_keeps_player_id(self):
        self.assertIn('"player_id":p["player_id"]',self.source)
        self.assertIn('str(x.get("player_id"))',self.grader)
    def test_all_markets_map_to_nflverse_stats(self):
        for market,stat in [
            ("player_pass_completions","completions"),
            ("player_pass_attempts","attempts"),
            ("player_rush_attempts","carries"),
            ("player_receptions","receptions"),
            ("player_pass_yds","passing_yards"),
            ("player_rush_yds","rushing_yards"),
            ("player_rec_yds","receiving_yards")]:
            self.assertIn(f'"{market}":"{stat}"',self.source)
    def test_grader_never_infers_missing_market_line(self):
        self.assertIn('result["dk_line"] is not None',self.grader)
        self.assertIn('("over","under")',self.grader)

if __name__=="__main__":
    unittest.main()
