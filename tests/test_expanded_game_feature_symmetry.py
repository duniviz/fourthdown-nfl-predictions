"""Guard against silently dropping away-team features from game ML inputs."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ExpandedGameFeatureTests(unittest.TestCase):
    def test_home_and_away_feature_ranges_are_symmetric(self):
        source = (ROOT / "research" / "expanded_game_feature_lab.py").read_text()
        tree = ast.parse(source)
        extended = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "extended" for target in node.targets)
        ]
        self.assertEqual(len(extended), 1)
        ranges = [
            node for node in ast.walk(extended[0].value)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name) and node.func.id == "range"
        ]
        self.assertEqual(len(ranges), 2)
        self.assertEqual(
            [ast.literal_eval(arg) for arg in ranges[0].args],
            [ast.literal_eval(arg) for arg in ranges[1].args],
            "Home and away expanded features must use the same indices",
        )

if __name__ == "__main__":
    unittest.main()
