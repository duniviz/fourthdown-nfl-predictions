import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.daily_forecast_refresh_window import daily_run_allowed
from scripts.check_pregame_forecast_window import FORECAST_FRESH, due, due_games_covered, recently_refreshed


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/publish-v2.yml"


class ForecastRefreshScheduleTests(unittest.TestCase):
    def test_clock_specific_jobs_declare_central_time(self):
        expected = {
            'tuesday-preforecast-evaluation.yml': "cron: '0 6 * * 2'",
            'nightly-game-grading.yml': "cron: '0 23 * * *'",
        }
        for filename, cron in expected.items():
            source = (ROOT / '.github/workflows' / filename).read_text()
            self.assertIn(cron + "\n      timezone: America/Chicago", source)

    def test_publish_keeps_daily_and_five_minute_forecast_checks(self):
        source = WORKFLOW.read_text()
        self.assertIn("cron: '8,38 * * * *'", source)
        self.assertNotIn("cron: '*/5 * * * *'", source)
        self.assertIn("scripts.pregame_window_wait", source)
        self.assertIn("cron: '17 23 * * *'", source)
        self.assertIn("cron: '17 22 * * *'", source)
        self.assertNotIn("timezone:", source)
        self.assertIn('TZ=America/Chicago date +%H)" != "17"', source)
        self.assertIn('scripts.daily_forecast_refresh_window', source)
        self.assertIn('scripts.check_pregame_forecast_window', source)

    def test_daily_forecast_runs_on_game_day_with_safe_buffer(self):
        kickoff = datetime(2026, 11, 17, 1, 15, tzinfo=timezone.utc)
        games = [{"kickoff_utc": kickoff.isoformat()}]
        self.assertEqual(daily_run_allowed(games, kickoff - timedelta(minutes=118))[0], True)
        self.assertEqual(daily_run_allowed(games, kickoff - timedelta(minutes=89))[0], False)
        self.assertEqual(daily_run_allowed(games, kickoff + timedelta(minutes=1))[0], False)

    def test_daily_forecast_runs_when_slate_has_no_game_today(self):
        now = datetime(2026, 11, 16, 23, 17, tzinfo=timezone.utc)
        thursday = now + timedelta(days=3)
        games = [{"kickoff_utc": thursday.isoformat()}]
        self.assertEqual(daily_run_allowed(games, now), (True, "No NFL game scheduled today"))

    def test_daily_forecast_fails_closed_without_a_verifiable_slate(self):
        now = datetime(2026, 11, 16, 23, 17, tzinfo=timezone.utc)
        self.assertFalse(daily_run_allowed([], now)[0])
        self.assertFalse(daily_run_allowed([{}], now)[0])

    def test_game_refresh_window_is_80_to_150_minutes(self):
        kickoff = datetime(2026, 11, 17, 1, 15, tzinfo=timezone.utc)
        self.assertEqual(FORECAST_FRESH, timedelta(hours=2))
        self.assertTrue(due([{"kickoff_utc": kickoff.isoformat()}], kickoff - timedelta(minutes=80)))
        self.assertTrue(due([{"kickoff_utc": kickoff.isoformat()}], kickoff - timedelta(minutes=115)))
        self.assertTrue(due([{"kickoff_utc": kickoff.isoformat()}], kickoff - timedelta(minutes=150)))
        self.assertFalse(due([{"kickoff_utc": kickoff.isoformat()}], kickoff - timedelta(minutes=79)))
        self.assertFalse(due([{"kickoff_utc": kickoff.isoformat()}], kickoff - timedelta(minutes=151)))
        now = kickoff - timedelta(minutes=104)
        games = [{"kickoff_utc": kickoff.isoformat()}]
        fresh = kickoff - timedelta(minutes=104)
        self.assertTrue(due_games_covered(games, fresh, now))
        self.assertFalse(due_games_covered(games, kickoff - timedelta(minutes=121), now))

    def test_recent_forecast_suppresses_duplicate_refreshes_for_45_minutes(self):
        now = datetime(2026, 11, 17, 0, 0, tzinfo=timezone.utc)
        self.assertTrue(recently_refreshed({"generated_at_utc": (now - timedelta(minutes=5)).isoformat()}, now))
        self.assertTrue(recently_refreshed({"generated_at_utc": (now - timedelta(minutes=44)).isoformat()}, now))
        self.assertFalse(recently_refreshed({"generated_at_utc": (now - timedelta(minutes=46)).isoformat()}, now))
        self.assertFalse(recently_refreshed({"generated_at_utc": (now + timedelta(minutes=1)).isoformat()}, now))

    def test_schedule_guard_runs_dynamic_window_and_serializes_writers(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("cron: '8,38 * * * *'", source)
        self.assertNotIn("cron: '*/5 * * * *'", source)
        self.assertIn("scripts.pregame_window_wait", source)
        self.assertIn("group: pregame-pipeline", source)
        self.assertIn("group: pregame-forecast-arm", source)
        arm = source.split("forecast:", 1)[0]
        self.assertNotIn("pregame-pipeline", arm)
        self.assertIn("scripts.check_pregame_forecast_window", source)
        self.assertIn("Generate current-season v2 forecasts", source)


if __name__ == "__main__":
    unittest.main()
