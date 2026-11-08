import unittest
from scripts.archive_pregame_player_lines import norm
from tools.match_dk_player_lines import norm as match_norm

class PlayerSuffixTests(unittest.TestCase):
    def test_junior(self):
        self.assertEqual(norm("Michael Penix Jr."), norm("Michael Penix"))
        self.assertEqual(norm("Michael Penix Junior"), norm("Michael Penix"))
    def test_roman(self):
        self.assertEqual(norm("Luther Burden III"), norm("Luther Burden"))
    def test_distinct(self):
        self.assertNotEqual(norm("Michael Penix"), norm("Michael Pittman"))
    def test_matcher_suffixes(self):
        self.assertEqual(match_norm("Kyle Pitts Sr."), match_norm("Kyle Pitts"))
        self.assertEqual(match_norm("Luther Burden III"), match_norm("Luther Burden"))
        self.assertNotEqual(match_norm("Kyle Pitts"), match_norm("Kyle Trask"))
    def test_punctuation(self):
        self.assertEqual(norm("D'Andre Swift"), norm("DAndre Swift"))

if __name__ == "__main__":
    unittest.main()
