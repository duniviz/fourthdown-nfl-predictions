import unittest
from datetime import datetime, timedelta, timezone
from live.pregame_integrity import inspect

class PregameIntegrityTests(unittest.TestCase):
    def test_missing_and_complete(self):
        kick=datetime(2026,11,8,14,30,tzinfo=timezone.utc)
        before=(kick-timedelta(minutes=20)).isoformat()
        game={'game_id':'game','kickoff_utc':kick.isoformat()}
        lock={'game_id':'game','forecast_at_utc':before,'captured_at_utc':before}
        row={'game_id':'game','kickoff':kick.isoformat(),'captured_at':before,'saved_at_utc':before,
             'dk_line':43.5,'dk_captured_at':before}
        issues, coverage=inspect([game],[],[],kick+timedelta(minutes=1))
        self.assertEqual(len(issues),2)
        self.assertEqual(inspect([game],[lock],[row],kick+timedelta(minutes=1)),([],[('game',1,1)]))
        row['saved_at_utc']=(kick+timedelta(seconds=1)).isoformat()
        self.assertTrue(inspect([game],[lock],[row],kick+timedelta(minutes=1))[0])

if __name__=='__main__':unittest.main()
