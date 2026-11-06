import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("build_game_context", Path(__file__).resolve().parents[1] / "tools" / "build_game_context.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class QBContextTests(unittest.TestCase):
    def test_reports_confirmed_out_without_guessing_starter(self):
        report = {"status": "verified", "source": "ESPN game summary", "players": [
            {"team": "BAL", "player": "QB One", "position": "QB", "status": "Out"},
            {"team": "BAL", "player": "QB Two", "position": "QB", "status": "Questionable"},
            {"team": "JAX", "player": "Receiver", "position": "WR", "status": "Out"},
        ]}
        result = module.qb_availability(report, "BAL", "JAX")
        self.assertEqual(result["BAL"]["confirmed_out"], [{"player": "QB One", "status": "Out"}])
        self.assertIsNone(result["BAL"]["expected_starter"])
        self.assertFalse(result["BAL"]["starter_verified"])
        self.assertEqual(result["JAX"]["confirmed_out"], [])
    def test_missing_feed_is_not_healthy_or_verified(self):
        result = module.qb_availability({"status": "unavailable"}, "BAL", "JAX")
        self.assertEqual(result["BAL"]["status"], "unavailable")
        self.assertFalse(result["BAL"]["starter_verified"])

if __name__ == "__main__":
    unittest.main()
