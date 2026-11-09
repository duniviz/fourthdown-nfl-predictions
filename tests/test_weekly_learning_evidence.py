import unittest
from scripts.verify_weekly_learning_evidence import build_evidence

class WeeklyLearningEvidenceTests(unittest.TestCase):
    def test_reports_only_same_week_frozen_matched_predictions(self):
        forecasts = []
        for week, kickoff, predicted in (
            (9, "2026-11-08T18:00:00+00:00", "2026-11-08T17:45:00+00:00"),
            (10, "2026-11-15T18:00:00+00:00", "2026-11-15T17:45:00+00:00"),
        ):
            gid = f"2026_{week:02d}_AAA_BBB"
            for model, value in (("live", 21), ("candidate", 20)):
                forecasts.append({"game_id":gid,"player_id":"P1","stat_key":"receiving_yards",
                    "model":model,"projection":value,"kickoff_utc":kickoff,"predicted_at_utc":predicted})
            for model, value in (("live", 40), ("candidate", 39)):
                forecasts.append({"game_id":gid,"player_id":"GAME","stat_key":"game_total",
                    "model":model,"projection":value,"kickoff_utc":kickoff,"predicted_at_utc":predicted})
        # A post-kickoff challenger must not enter the paired comparison.
        forecasts.append({"game_id":"2026_10_AAA_BBB","player_id":"P1","stat_key":"receiving_yards",
            "model":"leak","projection":999,"kickoff_utc":"2026-11-15T18:00:00+00:00",
            "predicted_at_utc":"2026-11-15T18:01:00+00:00"})
        players=[{"game_id":"2026_09_AAA_BBB","player_id":"P1","stat_key":"receiving_yards","actual":22},
                 {"game_id":"2026_10_AAA_BBB","player_id":"P1","stat_key":"receiving_yards","actual":22}]
        games=[]
        for week in (9,10):
            games.append({"game_id":f"2026_{week:02d}_AAA_BBB","home_score":21,"away_score":20})
        report=build_evidence(forecasts,players,games)
        self.assertEqual(report["week_tested"],"2026_week_10")
        self.assertEqual(report["matched_player_game_markets"],1)
        self.assertEqual(report["completed_games_tested"],1)
        comp={(x["market"],x["challenger"]):x for x in report["paired_challenger_comparisons"]}
        self.assertEqual(comp[("receiving_yards","candidate")]["matched_observations"],1)
        self.assertNotIn(("receiving_yards","leak"),comp)
        self.assertTrue(report["post_kickoff_forecasts_excluded"])

    def test_fails_if_no_prior_week_is_proven(self):
        with self.assertRaises(ValueError):
            build_evidence([],[],[])

if __name__ == "__main__":
    unittest.main()
