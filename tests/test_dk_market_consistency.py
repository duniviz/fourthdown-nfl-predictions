"""Fail-closed DK quote history integrity with legitimate future-game warnings."""
import copy
import datetime as dt
import unittest

from tools.audit_dk_market_consistency import audit

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 16, 0, 22, tzinfo=UTC)
EARLIER = "2026-11-15T18:00:00+00:00"
FUTURE = "2026-11-22T18:00:00+00:00"


def game(kickoff=EARLIER):
    return {"home": "KC", "away": "NYJ", "commence_time": kickoff,
            "home_spread": -3.5, "total": 44.5}


def history(kickoff=EARLIER, captured="2026-11-15T17:50:00Z"):
    return {f"NYJ|KC|{kickoff}": [
        {"captured_at_utc": captured, "home_spread": -3.5, "total": 44.5}
    ]}


class DKMarketIntegrityTests(unittest.TestCase):
    def check(self, rows, saved):
        return audit({"games": rows}, saved, NOW)

    def test_future_game_without_saved_history_warns_and_passes(self):
        errors, warnings, count = self.check([game(FUTURE)], {})
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertEqual(count, 1)

    def test_started_game_missing_history_fails(self):
        errors, warnings, _ = self.check([game()], {})
        self.assertEqual(len(errors), 1)
        self.assertIn("kickoff reached", errors[0])
        self.assertFalse(warnings)

    def test_started_game_postkickoff_only_history_fails(self):
        errors, _, _ = self.check([game()], history(captured="2026-11-15T18:01:00Z"))
        self.assertEqual(len(errors), 1)

    def test_started_game_pregame_quote_accepts_equivalent_utc_format(self):
        errors, warnings, _ = self.check([game()], history(kickoff="2026-11-15T18:00:00Z"))
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_market_sanity_still_blocks_future_games(self):
        invalid = {**game(FUTURE), "total": 120.0}
        errors, warnings, _ = self.check([invalid], {})
        self.assertTrue(any("Invalid total" in e for e in errors))
        self.assertEqual(len(warnings), 1)

    def test_duplicates_block_even_with_equivalent_timestamps(self):
        rows = [game(FUTURE), game("2026-11-22T18:00:00Z")]
        errors, warnings, count = self.check(rows, {})
        self.assertTrue(any("Duplicate DK game" in e for e in errors))
        self.assertEqual(count, 1)
        self.assertEqual(len(warnings), 2)

    def test_invalid_kickoff_cannot_be_silently_skipped(self):
        errors, warnings, _ = self.check([game("not-a-date")], {})
        self.assertTrue(any("Invalid kickoff timestamp" in e for e in errors))
        self.assertFalse(warnings)

    def test_exact_kickoff_requires_existing_history(self):
        now = dt.datetime(2026, 11, 15, 18, tzinfo=UTC)
        errors, warnings, _ = audit({"games": [game()]}, {}, now)
        self.assertEqual(len(errors), 1)
        self.assertFalse(warnings)

    def test_never_mutates_feed_or_saved_archive(self):
        odds, saved = {"games": [game(FUTURE)]}, history()
        a, b = copy.deepcopy(odds), copy.deepcopy(saved)
        audit(odds, saved, NOW)
        self.assertEqual(odds, a)
        self.assertEqual(saved, b)


if __name__ == "__main__":
    unittest.main()
