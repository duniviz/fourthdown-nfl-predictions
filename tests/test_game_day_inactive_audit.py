import unittest
from tools.audit_game_day_inactives import audit
class GameDayAuditTests(unittest.TestCase):
 def test_missing_report_never_active(self):
  result=audit({"games":[]},[{"game_id":"G1","player_id":"P1"}])
  self.assertEqual(result["unverified_games"],1)
  self.assertEqual(result["eligible_players"],0)
 def test_incomplete_team_report(self):
  result=audit({"games":[{"game_id":"G1","teams":[{"status":"confirmed"},{"status":"not_available"}],"official_source_url":"https://www.nfl.com/news/test","published_at":"2026-10-27T12:00:00Z"}]},[{"game_id":"G1"}])
  self.assertEqual(result["confirmed_source_games"],0)
if __name__=="__main__":unittest.main()
