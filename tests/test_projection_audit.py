import unittest
from live.projection_audit import audit

def player(**changes):
    p=dict(game_id="g1",team="TB",player_id="p1",player="Example QB",position="QB",stat_key="passing_yards",projection=220.0,expected_opportunities=33.0,games_used=5,last_5_avg=225.0)
    p.update(changes)
    return p

class ProjectionAuditTests(unittest.TestCase):
    def test_normal_qb(self):
        self.assertEqual(audit([player()])["summary"]["warning"],0)
    def test_low_attempts(self):
        report=audit([player(expected_opportunities=17.9,projection=116.4)])
        self.assertIn("qb_low_attempts",[f["code"] for f in report["flags"]])
    def test_duplicate(self):
        self.assertEqual(audit([player(),player()])["summary"]["error"],1)
    def test_multiple_qb_scenarios(self):
        report=audit([player(),player(player_id="p2",player="Backup QB")])
        self.assertIn("multiple_qb_starter_scenarios",[f["code"] for f in report["flags"]])
    def test_receiver_mismatch(self):
        report=audit([player(position="WR",stat_key="receiving_yards",projection=110,expected_opportunities=2)])
        self.assertIn("receiver_volume_mismatch",[f["code"] for f in report["flags"]])

if __name__=="__main__":
    unittest.main()
