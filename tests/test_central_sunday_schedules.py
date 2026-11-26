import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UniversalPregameScheduleTests(unittest.TestCase):
    def test_forecasts_and_game_capture_check_all_days(self):
        publish = (ROOT / '.github/workflows/publish-v2.yml').read_text()
        capture = (ROOT / '.github/workflows/capture-game-pregame.yml').read_text()
        self.assertIn("cron: '*/5 * * * *'", publish)
        self.assertIn("cron: '*/5 * * * *'", capture)
        self.assertIn('scripts/check_pregame_forecast_window.py', str(ROOT / 'scripts/check_pregame_forecast_window.py'))
        self.assertIn('python -m live.pregame_cycle', capture)
        self.assertNotIn('Sunday preset game-day refresh', capture)


if __name__ == '__main__':
    unittest.main()
