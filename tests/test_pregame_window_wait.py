import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from scripts.check_pregame_forecast_window import MAX_MINUTES, MIN_MINUTES
from scripts.pregame_window_wait import (
    CAPTURE_OPEN_MINUTES,
    CAPTURE_TARGET_MINUTES,
    FORECAST_TARGET_MINUTES,
    capture_plan,
    forecast_plan,
    gate,
)

CENTRAL = ZoneInfo("America/Chicago")


def at(day, hour, minute):
    return datetime(2026, 11, day, hour, minute, tzinfo=CENTRAL)


def sunday_games():
    return [
        {"game_id": "noon", "kickoff_utc": at(29, 12, 0).isoformat()},
        {"game_id": "early", "kickoff_utc": at(29, 15, 5).isoformat()},
        {"game_id": "late", "kickoff_utc": at(29, 15, 25).isoformat()},
        {"game_id": "night", "kickoff_utc": at(29, 19, 20).isoformat()},
    ]


class PregameWindowWaitTests(unittest.TestCase):
    def test_targets_stay_inside_the_existing_windows(self):
        self.assertLessEqual(MIN_MINUTES, FORECAST_TARGET_MINUTES)
        self.assertLessEqual(FORECAST_TARGET_MINUTES, 120)
        self.assertLessEqual(FORECAST_TARGET_MINUTES, MAX_MINUTES)
        self.assertLess(30, CAPTURE_TARGET_MINUTES)
        self.assertLessEqual(CAPTURE_TARGET_MINUTES, CAPTURE_OPEN_MINUTES)

    def test_sunday_morning_tick_waits_for_the_noon_forecast(self):
        decision = forecast_plan(sunday_games(), None, at(29, 8, 22))
        self.assertEqual(decision.action, "sleep")
        self.assertAlmostEqual(decision.seconds, (at(29, 10, 5) - at(29, 8, 22)).total_seconds(), delta=1)

    def test_noon_target_runs_and_groups_the_afternoon_kickoffs(self):
        games = sunday_games()
        self.assertEqual(forecast_plan(games, None, at(29, 10, 5)).action, "run")
        built = at(29, 10, 10)
        waiting = forecast_plan(games, built, at(29, 13, 0))
        self.assertEqual(waiting.action, "sleep")
        self.assertAlmostEqual(waiting.seconds, 30 * 60, delta=1)
        self.assertEqual(forecast_plan(games, built, at(29, 13, 30)).action, "run")

    def test_capture_starts_inside_t45_to_t30(self):
        games = sunday_games()
        early = capture_plan(games, at(29, 11, 0))
        self.assertEqual(early.action, "sleep")
        self.assertAlmostEqual(early.seconds, 18 * 60, delta=1)
        self.assertEqual(capture_plan(games, at(29, 11, 20)).action, "run")
        self.assertEqual(capture_plan(games, at(29, 11, 18)).action, "run")
        # 3:05 is 25 minutes away and already inside its lock; 3:25 is still at T-45.
        nxt = capture_plan(games, at(29, 14, 40), later_only=True)
        self.assertEqual(nxt.action, "run")

    def test_a_tick_hours_away_chains_and_a_far_tick_does_not(self):
        games = sunday_games()
        self.assertEqual(forecast_plan(games, None, at(29, 2, 0)).action, "chain")
        self.assertEqual(forecast_plan(games, None, at(28, 12, 0)).action, "skip")

    def test_manual_forecast_publishes_now_unless_it_asks_to_wait(self):
        now = at(28, 12, 0)
        self.assertEqual(gate("forecast", sunday_games(), None, now, event="workflow_dispatch").action, "run")
        self.assertEqual(
            gate("forecast", sunday_games(), None, now, event="workflow_dispatch", arm=True).action,
            "skip",
        )

    def test_a_stale_build_does_not_count_as_covering_the_kickoff(self):
        kickoff = at(29, 12, 0)
        games = [{"kickoff_utc": kickoff.isoformat()}]
        stale = kickoff - timedelta(hours=3)
        self.assertEqual(forecast_plan(games, stale, kickoff - timedelta(minutes=115)).action, "run")


if __name__ == "__main__":
    unittest.main()
