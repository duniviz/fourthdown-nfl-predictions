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

    def test_game_margin_dk_hit_rate_uses_signed_home_spread(self):
        rows=[]
        for model,projection in (("live",4),("challenger",0)):
            rows.append({"game_id":"2026_09_A_B","player_id":"GAME",
                "stat_key":"game_margin_home","model":model,"projection":projection,
                "actual":3,"dk_line":-2.5,"kickoff_utc":"2026-11-01T18:00:00Z",
                "predicted_at_utc":"2026-11-01T15:00:00Z"})
        report=compare(rows)
        metrics={x["model"]:x for x in report["metrics"]}
        self.assertEqual(metrics["live"]["dk_hit_rate"],1.0)
        self.assertEqual(metrics["challenger"]["dk_hit_rate"],0.0)
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
