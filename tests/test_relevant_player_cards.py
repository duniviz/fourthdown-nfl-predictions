import unittest
from pathlib import Path

class RelevantPlayerCardsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path("index.html").read_text(encoding="utf-8")

    def test_default_relevant_with_all_qualified_option(self):
        self.assertIn('<option value="relevant">Relevant players', self.html)
        self.assertIn('<option value="all">All qualified players', self.html)
        self.assertIn("fd-show-all-props", self.html)

    def test_all_six_markets_have_minimums(self):
        for market,minimum in (
            ("passing_yards",125),("rushing_yards",20),
            ("receiving_yards",20),("player_pass_completions",12),
            ("player_rush_attempts",5),("player_receptions",2)):
            self.assertIn(f"{market}:{minimum}",self.html)

    def test_upstream_player_filter_does_not_require_dk_line(self):
        self.assertIn("const players=started?archivedPlayers:playerResearch.filter(", self.html)
        self.assertNotIn("&&!unavailablePlayer(x)&&x.dk_line!==null", self.html)

    def test_no_changes_to_model_research(self):
        self.assertIn("Presentation-only relevance filter",self.html)
        self.assertIn("const allPropEntries=",self.html)
        self.assertIn("fd-low-priority",self.html)

if __name__=="__main__":
    unittest.main()
