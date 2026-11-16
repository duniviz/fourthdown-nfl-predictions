"""Regression checks for FOURTHDOWN's published refresh ownership and visibility."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class RefreshReliabilityTests(unittest.TestCase):
    def test_daily_non_game_forecast_and_dk_refresh_owners(self):
        publish=(ROOT/'.github/workflows/publish-v2.yml').read_text()
        odds=(ROOT/'.github/workflows/refresh-draftkings-odds.yml').read_text()
        daily_lines=(ROOT/'.github/workflows/daily-dk-player-props.yml').read_text()
        self.assertIn("cron: '17 22,23 * * *'", publish)
        self.assertIn("kickoff.astimezone(central).date()==today", publish)
        self.assertIn("cron: '40 21,22 * * *'", daily_lines)
        # The old hourly forecast cron was retired; Sunday now uses the
        # ordered DK -> forecast reusable workflow chain with a safe backstop.
        sunday=(ROOT/'.github/workflows/sunday-preset-game-day-refresh.yml').read_text()
        backstop=(ROOT/'.github/workflows/sunday-preset-backstop.yml').read_text()
        self.assertNotIn("cron: '7 * * * 0,1,4,5,6'", publish)
        self.assertIn("cron: '17 22,23 * * *'", publish)
        self.assertIn('uses: ./.github/workflows/daily-dk-player-props.yml', sunday)
        self.assertIn('uses: ./.github/workflows/publish-v2.yml', sunday)
        self.assertIn('needs: refresh-lines', sunday)
        self.assertIn('recovery_mode:', sunday)
        self.assertIn("const workflow_id = 'sunday-preset-game-day-refresh.yml'", backstop)
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
        self.assertIn('timeout-minutes: 45',capture)
        self.assertIn('timezone: America/Chicago',capture)
        self.assertIn('python -m live.pregame_capture_guard --mode cycle',capture)
        self.assertNotIn("cron: '2,12,22,32,42,52 * * * *'", capture)
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
