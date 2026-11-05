import unittest
from datetime import datetime,timedelta,timezone
from live.game_official_results import grade,summarize
from scripts.check_pregame_forecast_window import due

class OfficialResultsTests(unittest.TestCase):
    def setUp(self):
        self.row={"game_id":"2026_09_LV_SF","season":2026,"week":9,
            "home":"SF","away":"LV","kickoff_utc":"2026-11-08T21:25:00+00:00",
            "lock_status":"official","projected_margin_home":3,
            "projected_total":47,"dk_home_spread":-2.5,"dk_total":45.5}
        self.game={"game_id":"2026_09_LV_SF","home_team":"SF","away_team":"LV",
                   "home_score":24,"away_score":20}
    def test_grades_all_three(self):
        rows=grade([self.row],[self.game])
        self.assertEqual(len(rows),1)
        self.assertEqual([rows[0][x] for x in ("winner_result","ats_result","ou_result")],["hit","hit","miss"])
        self.assertEqual(summarize(rows)["winner"]["hit_pct"],100.0)
    def test_push_and_missing_market(self):
        row={**self.row,"dk_home_spread":-4,"dk_total":None}
        rows=grade([row],[self.game])
        self.assertEqual(rows[0]["ats_result"],"push")
        self.assertEqual(rows[0]["ou_result"],"not_available")
    def test_never_grade_unlocked_or_mismatched(self):
        self.assertEqual(grade([{**self.row,"lock_status":"pending"}],[self.game]),[])
        self.assertEqual(grade([self.row],[{**self.game,"home_team":"SEA"}]),[])
    def test_kickoff_guard(self):
        now=datetime(2026,11,8,20,tzinfo=timezone.utc)
        game=lambda m:{"kickoff_utc":(now+timedelta(minutes=m)).isoformat()}
        self.assertTrue(due([game(65)],now))
        self.assertFalse(due([game(20)],now))
        self.assertFalse(due([game(130)],now))
if __name__=="__main__":
    unittest.main()
