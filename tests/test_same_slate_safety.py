"""Fail-closed tests for identical-slate research comparisons."""
import unittest
from research.same_slate_leaderboard import compare

def row(model="live",line=59.5,projection=61,actual=65):
    return {"game_id":"2025_08_GB_CHI","player_id":"p1","stat_key":"receiving_yards",
            "model":model,"projection":projection,"actual":actual,"dk_line":line,
            "kickoff_utc":"2025-10-26T17:00:00Z","predicted_at_utc":"2025-10-26T16:20:00Z"}

class SameSlateSafetyTests(unittest.TestCase):
    def test_valid_same_slate(self):
        r=compare([row(),row("challenger",projection=62)])
        self.assertEqual(r["matched_slate_records"],1)
        self.assertFalse(r["promotion_allowed"])
    def test_duplicate_cannot_reenter(self):
        r=compare([row(),row(),row(),row("challenger")])
        self.assertEqual(r["matched_slate_records"],0)
        self.assertGreater(r["rejected"]["duplicate_model_forecast"],0)
    def test_conflicting_dk_lines_rejected(self):
        r=compare([row(),row("challenger",line=64.5)])
        self.assertEqual(r["matched_slate_records"],0)
        self.assertEqual(r["rejected"]["conflicting_dk_lines"],1)
    def test_post_kickoff_rejected(self):
        x=row();x["predicted_at_utc"]="2025-10-26T17:01:00Z"
        r=compare([x,row("challenger")])
        self.assertEqual(r["matched_slate_records"],0)
    def test_conflicting_actuals_rejected(self):
        r=compare([row(),row("challenger",actual=60)])
        self.assertEqual(r["matched_slate_records"],0)

if __name__=="__main__":unittest.main()
