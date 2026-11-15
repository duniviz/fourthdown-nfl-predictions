"""Coverage-audit regression cases: real-matchup IDs, timing, missing markets."""
import unittest
from datetime import datetime, timezone, timedelta
from scripts.postgame_evidence_coverage import evaluate, game_kickoff

NOW = datetime(2026, 11, 15, 23, 0, tzinfo=timezone.utc)
KICK = datetime(2026, 11, 15, 18, 0, tzinfo=timezone.utc)
GAME = {
    "game_id": "2026_10_BUF_NYJ", "gameday": "2026-11-15",
    "gametime": "13:00", "away_team": "BUF", "home_team": "NYJ",
    "away_score": 24, "home_score": 17,
}
LOCK = {
    "game_id": "2026_10_BUF_NYJ", "home": "NYJ", "away": "BUF",
    "kickoff_utc": KICK.isoformat(), "forecast_at_utc": (KICK-timedelta(hours=3)).isoformat(),
    "captured_at_utc": (KICK-timedelta(minutes=15)).isoformat(),
    "dk_at_utc": (KICK-timedelta(minutes=17)).isoformat(),
    "projected_margin_home": -4, "projected_total": 44,
    "dk_home_spread": 3.5, "dk_total": 45.5, "lock_status": "official"
}
PLAYER = {"game_id": GAME["game_id"], "actual": 81, "dk_line": 72.5}
SHADOW = {"game_id": GAME["game_id"], "model": "ridge", "projection": 41}


class AuditTests(unittest.TestCase):
    def evaluate(self, games=None, locks=None, grades=None, players=None, shadows=None):
        return evaluate([GAME] if games is None else games,
                        [LOCK] if locks is None else locks,
                        [{"game_id": GAME["game_id"]}] if grades is None else grades,
                        [PLAYER] if players is None else players,
                        [SHADOW] if shadows is None else shadows, NOW)

    def test_scheduled_game_kickoff_timezone(self):
        self.assertEqual(game_kickoff(GAME), KICK)

    def test_full_evidence_is_complete(self):
        r = self.evaluate()
        self.assertEqual(r["audited_games"], 1)
        self.assertEqual(r["complete_games"], 1)

    def test_early_lock_not_mistaken_for_t15(self):
        r = self.evaluate(locks=[{**LOCK, "lock_status": "early_pregame"}])
        self.assertIn("official_t15_lock_missing", r["games"][0]["issues"])

    def test_missing_finals_grades_and_lines_flagged(self):
        game = {**GAME, "home_score": None}
        lock = {**LOCK, "dk_total": None, "dk_home_spread": None}
        r = self.evaluate(games=[game], locks=[lock], grades=[], players=[], shadows=[])
        for issue in ("final_score_unavailable", "game_grading_row_missing",
                      "frozen_dk_total_missing", "frozen_dk_spread_missing",
                      "player_grading_evidence_missing", "paired_shadow_archive_unverified"):
            self.assertIn(issue, r["games"][0]["issues"])

    def test_postkickoff_lock_excluded(self):
        late = {**LOCK, "captured_at_utc": (KICK+timedelta(minutes=3)).isoformat()}
        r = self.evaluate(locks=[late])
        self.assertIn("valid_frozen_game_projection_missing", r["games"][0]["issues"])

    def test_game_with_no_lock_is_still_in_report(self):
        r = self.evaluate(locks=[])
        self.assertEqual(r["audited_games"], 1)
        self.assertIn("valid_frozen_game_projection_missing", r["games"][0]["issues"])

    def test_future_game_not_prematurely_flagged(self):
        game = {**GAME, "gameday": "2026-11-16"}
        self.assertEqual(self.evaluate(games=[game])["audited_games"], 0)


if __name__ == "__main__":
    unittest.main()
