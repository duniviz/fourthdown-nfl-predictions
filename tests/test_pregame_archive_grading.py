"""Guard against regressions in pregame DK archive grading keys."""
import unittest
from pathlib import Path

class PregameArchiveGradingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=Path("scripts/archive_pregame_player_lines.py").read_text()
        cls.grader=Path("live/player_results.py").read_text()
    def test_capture_keeps_player_id(self):
        self.assertIn('"player_id":p.get("player_id")',self.source)
        self.assertIn('str(x.get("player_id"))',self.grader)
    def test_all_markets_map_to_nflverse_stats(self):
        for market,stat in [
            ("player_passing_completions","completions"),
            ("player_passing_attempts","attempts"),
            ("player_rushing_attempts","carries"),
            ("player_receptions","receptions"),
            ("player_passing_yards","passing_yards"),
            ("player_rushing_yards","rushing_yards"),
            ("player_receiving_yards","receiving_yards")]:
            self.assertIn(f'"{market}":"{stat}"',self.source)
    def test_grader_never_infers_missing_market_line(self):
        self.assertIn('result["dk_line"] is not None',self.grader)
        self.assertIn('("over","under")',self.grader)

if __name__=="__main__":
    unittest.main()
