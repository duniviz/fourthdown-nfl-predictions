import unittest
from scripts.archive_pregame_player_lines import norm

class PlayerSuffixTests(unittest.TestCase):
    def test_junior(self):
        self.assertEqual(norm("Michael Penix Jr."), norm("Michael Penix"))
        self.assertEqual(norm("Michael Penix Junior"), norm("Michael Penix"))
    def test_roman(self):
        self.assertEqual(norm("Luther Burden III"), norm("Luther Burden"))
    def test_distinct(self):
        self.assertNotEqual(norm("Michael Penix"), norm("Michael Pittman"))
    def test_punctuation(self):
        self.assertEqual(norm("D'Andre Swift"), norm("DAndre Swift"))

if __name__ == "__main__":
    unittest.main()
