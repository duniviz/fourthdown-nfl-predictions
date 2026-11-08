import unittest

from live.pregame_refresh_state import reserved_attempt, record_result

class PregameRefreshStateTests(unittest.TestCase):
    def test_failure_does_not_mark_slate_complete_and_allows_one_retry(self):
        state, reserved, pending, attempt = reserved_attempt({}, 0, ["kickoff"], "2026-11-08T16:00:00+00:00")
        self.assertEqual((reserved, pending, attempt), (2, ["kickoff"], (1, {"game", "player"})))
        state = record_result(state, pending, attempt[0], {"game":False,"player":False}, backup_ok=False)
        self.assertNotIn("kickoff", state["slates"])
        state, reserved, pending, attempt = reserved_attempt(state, 2, ["kickoff"], "2026-11-08T16:05:00+00:00")
        self.assertEqual((reserved, pending, attempt), (2, ["kickoff"], (2, {"game", "player"})))

    def test_success_marks_complete_and_prevents_paid_repeat(self):
        state, _, pending, attempt = reserved_attempt({}, 0, ["kickoff"], "stamp")
        state = record_result(state, pending, attempt[0], {"game":True,"player":True}, backup_ok=True)
        self.assertEqual(state["slates"], ["kickoff"])
        state, reserved, pending, attempt = reserved_attempt(state, 2, ["kickoff"], "later")
        self.assertEqual((reserved, pending, attempt), (2, [], None))

    def test_retry_budget_is_reserved_and_failure_is_recorded_after_second_attempt(self):
        state, _, pending, attempt = reserved_attempt({}, 0, ["kickoff"], "stamp")
        state = record_result(state, pending, attempt[0], {"game":False,"player":False}, backup_ok=False)
        state, _, pending, attempt = reserved_attempt(state, 2, ["kickoff"], "stamp2")
        state = record_result(state, pending, attempt[0], {"game":False,"player":False}, backup_ok=False)
        self.assertNotIn("kickoff", state["slates"])
        self.assertIn("kickoff", state["failed_slates"])
        state, reserved, pending, attempt = reserved_attempt(state, 4, ["kickoff"], "stamp3")
        self.assertEqual((reserved, pending, attempt), (4, [], None))

    def test_monthly_budget_exhaustion_does_not_call_provider(self):
        state, reserved, pending, result = reserved_attempt({}, 124, ["kickoff"], "stamp")
        self.assertEqual((reserved, pending, result), (124, ["kickoff"], "budget_exhausted"))
        self.assertIn("kickoff", state["failed_slates"])

    def test_retry_only_reserves_and_calls_failed_provider(self):
        state, requests, pending, attempt = reserved_attempt({}, 0, ["kickoff"], "stamp")
        self.assertEqual(requests, 2)
        state = record_result(state, pending, attempt[0], {"game":True,"player":False}, backup_ok=True)
        state, requests, pending, attempt = reserved_attempt(state, 2, ["kickoff"], "stamp2")
        self.assertEqual(requests, 1)
        self.assertEqual(attempt, (2,{"player"}))

if __name__ == "__main__":
    unittest.main()
