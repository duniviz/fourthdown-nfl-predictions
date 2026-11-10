import unittest
from live.player_research import aggregate_player_history, current_roster_team

class CurrentRosterTeamTests(unittest.TestCase):
    def setUp(self):
        self.starters = {
            ("game-min", "MIN", "QB"): [
                {"player": "Kirk Cousins", "team": "MIN", "position": "QB", "status": "projected"}
            ],
            ("game-min", "MIN", "WR"): [
                {"player": "Justin Jefferson", "team": "MIN", "position": "WR", "status": "projected"}
            ],
            ("game-nyg", "NYG", "QB"): [
                {"player": "J.J. McCarthy", "team": "NYG", "position": "QB", "status": "projected"}
            ],
        }

    def test_traded_player_uses_current_slate_team(self):
        self.assertEqual(current_roster_team(self.starters, "Kirk Cousins"), "MIN")

    def test_regular_roster_player_uses_current_team(self):
        self.assertEqual(current_roster_team(self.starters, "Justin Jefferson"), "MIN")

    def test_unlisted_player_falls_back_to_historical_team(self):
        self.assertIsNone(current_roster_team(self.starters, "Former Backup"))

    def test_ambiguous_same_name_fails_closed(self):
        starters = dict(self.starters)
        starters[("game-lv", "LV", "QB")] = [
            {"player": "Kirk Cousins", "team": "LV", "position": "QB", "status": "projected"}
        ]
        self.assertIsNone(current_roster_team(starters, "Kirk Cousins"))

    def test_history_across_teams_is_combined_once_per_player(self):
        history = {
            ("LV", "cousins-id"): [{"team":"LV","week":3,"passing_yards":210}],
            ("MIN", "cousins-id"): [{"team":"MIN","week":8,"passing_yards":260}],
        }
        merged = aggregate_player_history(history)
        self.assertEqual(list(merged), ["cousins-id"])
        self.assertEqual([r["team"] for r in merged["cousins-id"]], ["LV","MIN"])
        self.assertEqual(len(merged["cousins-id"]), 2)

if __name__ == "__main__":
    unittest.main()
