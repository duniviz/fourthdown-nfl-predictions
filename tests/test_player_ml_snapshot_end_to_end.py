import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import capture_pregame_snapshots as capture


class PlayerMLSnapshotEndToEndTests(unittest.TestCase):
    def test_pregame_projection_ml_shadow_and_dk_line_reach_player_history(self):
        kickoff = datetime(2026, 11, 15, 19, 0, tzinfo=timezone.utc)
        now = kickoff - timedelta(minutes=25)
        forecast_at = kickoff - timedelta(minutes=60)
        quote_at = kickoff - timedelta(minutes=30)
        game_id = "2026_11_GB_CHI"

        player = {
            "game_id": game_id,
            "player_id": "00-0000001",
            "player": "Test Receiver",
            "team": "GB",
            "opponent": "CHI",
            "market_key": "player_rec_yds",
            "stat_key": "receiving_yards",
            "market": "Receiving yards",
            "projection": 57.0,
            "generated_at_utc": forecast_at.isoformat(),
            "player_ml_shadow": {
                "family": "paired-ridge-v1",
                "baseline": 57.0,
                "candidate": 54.5,
                "active": False,
            },
        }
        quote = {
            "game_id": game_id,
            "player_id": player["player_id"],
            "player": player["player"],
            "market_key": "player_rec_yds",
            "line": 49.5,
            "bookmaker": "draftkings",
            "away_team": "GB",
            "home_team": "CHI",
            "commence_time": kickoff.isoformat(),
            "observed_at_utc": quote_at.isoformat(),
        }

        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            fixtures = {
                "live-v2.json": {"games": [{
                    "game_id": game_id,
                    "home": "CHI",
                    "away": "GB",
                    "kickoff_utc": kickoff.isoformat(),
                }]},
                "player-research.json": {
                    "generated_at_utc": forecast_at.isoformat(),
                    "players": [player],
                },
                "count-projections.json": {"players": []},
                "dk-odds.json": {"bookmaker": "draftkings", "rows": [quote]},
                "pregame-snapshots.json": {"records": []},
                "player-history.json": {"players": []},
                "weather.json": {"games": {}},
            }
            for name, payload in fixtures.items():
                (data / name).write_text(json.dumps(payload), encoding="utf-8")

            captured = capture.collect(data, now)

            saved_snapshots = json.loads((data / "pregame-snapshots.json").read_text())["records"]
            saved_history = json.loads((data / "player-history.json").read_text())["players"]

        self.assertEqual(len(captured), 1)
        self.assertEqual(len(saved_snapshots), 1)
        self.assertEqual(len(saved_history), 1)
        row = saved_history[0]
        self.assertEqual((row["game_id"], row["player_id"], row["stat_key"]),
                         (game_id, player["player_id"], "receiving_yards"))
        self.assertEqual(row["projection"], 57.0)
        self.assertEqual(row["dk_line"], 49.5)
        self.assertEqual(row["player_ml_shadow"]["candidate"], 54.5)
        self.assertEqual(row["recommended_side"], "OVER")
        saved_at = datetime.fromisoformat(row["saved_at_utc"])
        self.assertLess(saved_at, kickoff - timedelta(minutes=15))


if __name__ == "__main__":
    unittest.main()
