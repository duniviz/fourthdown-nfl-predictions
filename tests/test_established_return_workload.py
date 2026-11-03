import unittest

from live.player_research import established_return_workload


def game(week, carries, snap=None):
    row={"week":str(week),"carries":str(carries)}
    if snap is not None:
        row["offense_pct"]=str(snap)
    return row


class EstablishedReturnWorkloadTests(unittest.TestCase):
    def test_blends_prior_full_games_with_reduced_current_role(self):
        prior=[game(14,16),game(15,18),game(16,14),game(17,17),game(18,15)]
        current=[game(7,6,42),game(8,8,51)]
        result=established_return_workload(current,prior,"carries","active")
        self.assertIsNotNone(result)
        self.assertEqual(result["full_games_used"],5)
        self.assertGreater(result["blended_carries"],7)
        self.assertLess(result["blended_carries"],16)
        self.assertEqual(result["snap_share_signal"],.465)

    def test_questionable_status_uses_lower_role_case(self):
        prior=[game(14,16),game(15,18),game(16,14),game(17,17),game(18,15)]
        current=[game(7,8),game(8,8)]
        active=established_return_workload(current,prior,"carries","active")
        questionable=established_return_workload(current,prior,"carries","questionable")
        self.assertLessEqual(questionable["blended_carries"],active["blended_carries"])

    def test_does_not_apply_to_new_or_established_current_roles(self):
        self.assertIsNone(established_return_workload([game(1,5)], [game(1,7),game(2,5)], "carries"))
        self.assertIsNone(established_return_workload([game(1,8),game(2,8),game(3,8)], [game(1,12)]*5, "carries"))


if __name__ == "__main__":
    unittest.main()
