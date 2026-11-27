import unittest
from datetime import datetime,timedelta,timezone
from live.game_official_results import grade,nightly_grade_due,summarize
from scripts.check_pregame_forecast_window import due

class OfficialResultsTests(unittest.TestCase):
    def setUp(self):
        self.row={"game_id":"2026_09_LV_SF","season":2026,"week":9,
            "home":"SF","away":"LV","kickoff_utc":"2026-11-08T21:25:00+00:00",
            "lock_status":"official","forecast_at_utc":"2026-11-08T20:50:00+00:00",
            "captured_at_utc":"2026-11-08T21:00:00+00:00","dk_at_utc":"2026-11-08T20:55:00+00:00","projected_margin_home":3,
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
    def test_forecast_only_counts_winner_without_odds(self):
        row={**self.row,"lock_status":"forecast_only","dk_home_spread":None,"dk_total":None,"dk_at_utc":None}
        result=grade([row],[self.game])[0]
        self.assertEqual(result["winner_result"],"hit")
        self.assertEqual(result["ats_result"],"not_available")
        self.assertEqual(result["ou_result"],"not_available")

    def test_postkickoff_forecast_or_quote_is_not_used(self):
        self.assertEqual(grade([{**self.row,"captured_at_utc":"2026-11-08T21:25:00+00:00"}],[self.game]),[])
        result=grade([{**self.row,"dk_at_utc":"2026-11-08T21:26:00+00:00"}],[self.game])[0]
        self.assertEqual(result["winner_result"],"hit")
        self.assertEqual(result["ats_result"],"not_available")

    def test_pit_cin_lock_grades_when_the_final_score_is_present(self):
        lock={"game_id":"2026_10_PIT_CIN","season":2026,"week":10,"home":"CIN","away":"PIT",
              "kickoff_utc":"2026-11-16T01:20:00+00:00","lock_status":"last_available",
              "lock_cutoff_utc":"2026-11-16T01:05:00+00:00",
              "forecast_at_utc":"2026-11-16T00:05:11+00:00",
              "captured_at_utc":"2026-11-16T01:13:01+00:00",
              "dk_at_utc":"2026-11-15T20:39:09+00:00",
              "projected_margin_home":2.49,"projected_total":49.31,
              "dk_home_spread":-3.5,"dk_total":49.5}
        game={"game_id":"2026_10_PIT_CIN","home_team":"CIN","away_team":"PIT",
              "home_score":20,"away_score":17}
        rows=grade([lock],[game])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["winner_result"],"hit")
        self.assertEqual(rows[0]["ats_result"],"hit")
    def test_delayed_nightly_run_grades_the_missed_sunday_final(self):
        last=datetime(2026,11,16,4,15,tzinfo=timezone.utc)
        morning=datetime(2026,11,16,12,31,tzinfo=timezone.utc)
        self.assertTrue(nightly_grade_due(morning,last,"schedule"))
        on_time=datetime(2026,11,17,5,5,tzinfo=timezone.utc)
        self.assertTrue(nightly_grade_due(on_time,last,"schedule"))
        graded=datetime(2026,11,17,5,10,tzinfo=timezone.utc)
        later_morning=datetime(2026,11,17,12,30,tzinfo=timezone.utc)
        self.assertFalse(nightly_grade_due(later_morning,graded,"schedule"))
        self.assertFalse(nightly_grade_due(morning,last,"pull_request"))
        self.assertTrue(nightly_grade_due(morning,last,"workflow_dispatch"))
    def test_kickoff_guard(self):
        now=datetime(2026,11,8,20,tzinfo=timezone.utc)
        game=lambda m:{"kickoff_utc":(now+timedelta(minutes=m)).isoformat()}
        self.assertTrue(due([game(80)],now))
        self.assertTrue(due([game(115)],now))
        self.assertTrue(due([game(150)],now))
        self.assertFalse(due([game(79)],now))
        self.assertFalse(due([game(151)],now))
if __name__=="__main__":
    unittest.main()
