"""Regression checks for FOURTHDOWN's refresh ownership and feed visibility."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class RefreshReliabilityTests(unittest.TestCase):
    def test_daily_forecast_and_dynamic_pregame_refresh_owners(self):
        publish=(ROOT/'.github/workflows/publish-v2.yml').read_text()
        daily_lines=(ROOT/'.github/workflows/daily-dk-player-props.yml').read_text()
        self.assertIn("cron: '*/5 * * * *'", publish)
        self.assertIn("cron: '17 23 * * *'", publish)
        self.assertIn("cron: '17 22 * * *'", publish)
        window=(ROOT/'scripts/check_pregame_forecast_window.py').read_text()
        self.assertIn('MIN_MINUTES = 40', window)
        self.assertIn('MAX_MINUTES = 60', window)
        self.assertIn('FRESH_MINUTES = 45', window)
        self.assertIn('python -m scripts.daily_forecast_refresh_window', publish)
        self.assertIn('python -m scripts.check_pregame_forecast_window', publish)
        self.assertIn("cron: '40 16 * * *'", daily_lines)
        self.assertIn("cron: '10,40 17 * * *'", daily_lines)
        self.assertNotIn("cron: '37 * * * 1,4,5,6'", daily_lines)
        self.assertIn('Verify refreshed production timestamps before publishing',publish)
        self.assertIn('REFRESH_FAILED',publish)

    def test_single_dynamic_game_day_capture_owner(self):
        capture=(ROOT/'.github/workflows/capture-game-pregame.yml').read_text()
        self.assertIn("cron: '*/5 * * * *'",capture)
        self.assertIn('group: pregame-pipeline',capture)
        self.assertIn('python -m live.pregame_cycle',capture)
        self.assertIn('python -m live.pregame_capture_guard --mode cycle',capture)
        self.assertNotIn('timezone:',capture)
        self.assertNotIn('Sunday preset game-day refresh',capture)
        self.assertNotIn('freeze_pregame_game_challengers',capture)

    def test_homepage_displays_actual_feed_timestamps(self):
        homepage=(ROOT/'index.html').read_text()
        script=(ROOT/'assets/feed-freshness.js').read_text()
        self.assertIn('assets/feed-freshness.js',homepage)
        self.assertIn("fetch('data/live-v2.json?freshness='",script)
        self.assertIn("fetch('data/dk-game-odds.json?freshness='",script)
        self.assertIn('forecast.generated_at_utc',script)
        self.assertIn('odds.snapshot_date_utc',script)
        self.assertIn('FD_STALE_LINE_HOURS',script)
        self.assertIn('generated_at_utc',script)
        self.assertIn('snapshot_date_utc',script)
        self.assertIn('Warning ·',script)
        self.assertIn('window.location.reload()',script)

if __name__=='__main__':
    unittest.main()
