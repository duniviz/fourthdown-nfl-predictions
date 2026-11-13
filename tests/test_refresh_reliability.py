"""Regression checks for FOURTHDOWN's published refresh ownership and visibility."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class RefreshReliabilityTests(unittest.TestCase):
    def test_one_nightly_forecast_owner(self):
        publish=(ROOT/'.github/workflows/publish-v2.yml').read_text()
        odds=(ROOT/'.github/workflows/refresh-draftkings-odds.yml').read_text()
        self.assertIn("cron: '17 22,23 * * 2,3,6'", publish)
        self.assertIn("cron: '7 * * * 0,1,4,5,6'", publish)
        self.assertIn('TZ=America/Chicago',publish)
        self.assertIn('!= "17"',publish)
        self.assertNotIn('  schedule:',odds)
        self.assertIn('Verify refreshed production timestamps before publishing',publish)
        self.assertIn('REFRESH_FAILED',publish)
        self.assertIn('Publishing new forecast separately',publish)
        self.assertIn('if label == \'forecast\':',publish)

    def test_pregame_locks_are_not_queued_behind_forecasts(self):
        capture=(ROOT/'.github/workflows/capture-game-pregame.yml').read_text()
        self.assertIn('group: pregame-pipeline',capture)
        self.assertIn('python -m live.pregame_cycle',capture)
        self.assertIn('timeout-minutes: 10',capture)
        self.assertIn("cron: '7,22,37,52 * * * *'", capture)
        self.assertNotIn('freeze_pregame_game_challengers',capture)

    def test_homepage_displays_actual_feed_timestamps(self):
        homepage=(ROOT/'index.html').read_text()
        script=(ROOT/'assets/feed-freshness.js').read_text()
        self.assertIn('assets/feed-freshness.js',homepage)
        self.assertIn('America/Chicago',script)
        self.assertIn('generated_at_utc',script)
        self.assertIn('snapshot_date_utc',script)
        self.assertIn('data may be stale',script)
        self.assertIn('window.location.reload()',script)

if __name__=='__main__':
    unittest.main()
