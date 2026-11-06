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

    def test_build_writes_qb_context_without_postgame_starter_inference(self):
        import json
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "live.json"
            output = Path(directory) / "context.json"
            source.write_text(json.dumps({"games": [{
                "game_id": "2026_09_BAL_JAX", "away": "BAL", "home": "JAX",
                "kickoff_utc": "2026-11-05T20:00:00Z"
            }]}), encoding="utf-8")
            report = {"status": "verified", "source": "ESPN game summary", "players": [
                {"team": "BAL", "player": "Starting QB", "position": "QB", "status": "Out"}
            ]}
            with patch.object(module, "event_for_game", return_value=None), \
                 patch.object(module, "rest_context", return_value={"status": "unavailable"}), \\
                 patch.object(module, "recent_results", return_value={"status": "unavailable"}), \\
                 patch.object(module, "prior_meetings", return_value={"status": "unavailable"}), \\
                 patch.object(module, "injury_context", return_value=report):
                module.build(source, output)
            game = json.loads(output.read_text(encoding="utf-8"))["games"]["2026_09_BAL_JAX"]
            self.assertEqual(game["quarterbacks"]["BAL"]["confirmed_out"][0]["player"], "Starting QB")
            self.assertIsNone(game["quarterbacks"]["BAL"]["expected_starter"])
            self.assertFalse(game["quarterbacks"]["BAL"]["starter_verified"])

if __name__ == "__main__":
    unittest.main()
