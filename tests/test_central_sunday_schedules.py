import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UniversalPregameScheduleTests(unittest.TestCase):
    def test_dynamic_refresh_schedules_cover_every_game_day(self):
        publish = (ROOT / '.github/workflows/publish-v2.yml').read_text()
        capture = (ROOT / '.github/workflows/capture-game-pregame.yml').read_text()
        guard = (ROOT / 'scripts/check_pregame_forecast_window.py').read_text()
        self.assertIn("cron: '*/5 * * * *'", publish)
        self.assertIn("cron: '*/5 * * * *'", capture)
        self.assertIn('MIN_MINUTES = 40', guard)
        self.assertIn('MAX_MINUTES = 60', guard)
        self.assertIn('python -m live.pregame_cycle', capture)
        self.assertNotIn('Sunday preset game-day refresh', capture)


if __name__ == '__main__':
    unittest.main()
