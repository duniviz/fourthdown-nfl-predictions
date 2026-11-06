import unittest
from datetime import datetime, timedelta, timezone
from live.verify_game_pregame_locks import missing_locks

class LockVerificationTests(unittest.TestCase):
 def test_missing_recent_kickoff_fails(self):
  now=datetime(2026,11,6,1,20,tzinfo=timezone.utc)
  games=[{"game_id":"2026_09_JAX_BAL","kickoff_utc":"2026-11-06T01:15:00+00:00"}]
  self.assertEqual(missing_locks(games,[],now),["2026_09_JAX_BAL"])
  self.assertEqual(missing_locks(games,[{"game_id":"2026_09_JAX_BAL","lock_status":"official"}],now),[])
 def test_future_and_old_games_do_not_fail(self):
  now=datetime(2026,11,6,1,20,tzinfo=timezone.utc)
  games=[{"game_id":"future","kickoff_utc":(now+timedelta(minutes=10)).isoformat()},
         {"game_id":"old","kickoff_utc":(now-timedelta(hours=3)).isoformat()}]
  self.assertEqual(missing_locks(games,[],now),[])

if __name__=="__main__":unittest.main()
