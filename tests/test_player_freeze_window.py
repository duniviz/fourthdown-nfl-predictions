import unittest
from datetime import datetime, timedelta, timezone

from live.player_results import select_frozen_ml_pairs


class PlayerFreezeWindowTests(unittest.TestCase):
    def row(self, saved_minutes, forecast_minutes=None):
        kickoff = datetime(2026, 11, 19, 1, 15, tzinfo=timezone.utc)
        saved = kickoff - timedelta(minutes=saved_minutes)
        forecast = saved - timedelta(minutes=1 if forecast_minutes is None else forecast_minutes)
        return {
            "game_id": "2026_11_KC_DEN",
            "player_id": "p1",
            "stat_key": "receiving_yards",
            "kickoff_utc": kickoff.isoformat(),
            "forecast_captured_at_utc": forecast.isoformat(),
            "saved_at_utc": saved.isoformat(),
            "player_ml_shadow": {"baseline": 45.0, "candidate": 48.0},
        }

    def test_selects_latest_pair_saved_inside_t30_window(self):
        rows = [self.row(31), self.row(30), self.row(8)]
        selected = select_frozen_ml_pairs(rows)
        pair = selected[("2026_11_KC_DEN", "p1", "receiving_yards")][1]
        self.assertEqual(pair["candidate"], 48.0)
        self.assertEqual(selected[("2026_11_KC_DEN", "p1", "receiving_yards")][0][0],
                         datetime(2026, 11, 19, 1, 7, tzinfo=timezone.utc))

    def test_excludes_outside_or_at_kickoff_and_future_forecast(self):
        self.assertEqual(select_frozen_ml_pairs([self.row(31)]), {})
        self.assertEqual(select_frozen_ml_pairs([self.row(0)]), {})
        future_forecast = self.row(10, forecast_minutes=-1)
        self.assertEqual(select_frozen_ml_pairs([future_forecast]), {})


if __name__ == "__main__":
    unittest.main()
