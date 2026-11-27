import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UniversalPregameScheduleTests(unittest.TestCase):
    def test_dynamic_refresh_schedules_cover_every_game_day(self):
        publish = (ROOT / '.github/workflows/publish-v2.yml').read_text()
        capture = (ROOT / '.github/workflows/capture-game-pregame.yml').read_text()
        guard = (ROOT / 'scripts/check_pregame_forecast_window.py').read_text()
        self.assertIn("cron: '8,38 * * * *'", publish)
        self.assertIn("cron: '8,38 * * * *'", capture)
        self.assertNotIn("cron: '*/5 * * * *'", publish)
        self.assertNotIn("cron: '*/5 * * * *'", capture)
        self.assertIn('MIN_MINUTES = 80', guard)
        self.assertIn('MAX_MINUTES = 150', guard)
        self.assertIn('FORECAST_FRESH = timedelta(hours=2)', guard)
        self.assertIn('python -m live.pregame_cycle', capture)
        self.assertNotIn('Sunday preset game-day refresh', capture)


if __name__ == '__main__':
    unittest.main()
