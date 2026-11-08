"""Contract checks for the pregame capture -> Wednesday game-grading bridge."""
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from research.import_official_game_locks import merge

ROOT = Path(__file__).resolve().parents[1]

class PipelineIntegrationTests(unittest.TestCase):
    def test_challengers_survive_official_lock_import(self):
        kickoff = datetime(2026, 11, 8, 18, tzinfo=timezone.utc)
        cutoff = kickoff - timedelta(minutes=15)
        existing = [
            {"game_id": "game1", "player_id": "GAME", "stat_key": "game_total",
             "model": "live", "projection": 43.0, "source": "frozen production game projection"},
            {"game_id": "game1", "player_id": "GAME", "stat_key": "game_total",
             "model": "ml_ridge", "projection": 42.0, "source": "pregame challenger"},
        ]
        lock = {
            "game_id": "game1", "lock_status": "official",
            "kickoff_utc": kickoff.isoformat(),
            "lock_cutoff_utc": cutoff.isoformat(),
            "forecast_at_utc": (cutoff - timedelta(minutes=5)).isoformat(),
            "dk_at_utc": (cutoff - timedelta(minutes=5)).isoformat(),
            "captured_at_utc": (cutoff - timedelta(minutes=4)).isoformat(),
            "projected_total": 44.0, "dk_total": 43.5,
        }
        rows, added, rejected = merge([lock], existing)
        by_model = {row["model"]: row for row in rows}
        self.assertEqual((added, rejected), (1, 0))
        self.assertEqual(by_model["live"]["projection"], 44.0)
        self.assertEqual(by_model["ml_ridge"], existing[1])
        self.assertEqual(merge([lock], rows)[1:], (0, 0))

    def test_capture_wiring_and_persistence(self):
        workflow = (ROOT / ".github/workflows/capture-game-pregame.yml").read_text()
        self.assertNotIn("python -m research.freeze_pregame_game_challengers", workflow)
        independent = (ROOT / ".github/workflows/freeze-game-ml-challengers.yml").read_text()
        self.assertIn("python -m research.freeze_pregame_game_challengers", independent)
        self.assertIn("python -m research.game_ml_freeze_guard", independent)
        self.assertIn("data/weekly-shadow-forecasts.json", independent)
        self.assertNotIn("data/weekly-shadow-forecasts.json", workflow)
        self.assertIn("python -m live.pregame_cycle", workflow)

    def test_weekly_wiring_uses_selected_branch(self):
        workflow = (ROOT / ".github/workflows/fourthdown-unified-weekly-ml.yml").read_text()
        self.assertIn("ref: ${{ github.ref_name }}", workflow)
        self.assertIn("python -m research.import_official_game_locks", workflow)
        self.assertIn("python research/grade_paired_game_models.py", workflow)
        self.assertIn("data/weekly-shadow-forecasts.json", workflow)

if __name__ == "__main__":
    unittest.main()
