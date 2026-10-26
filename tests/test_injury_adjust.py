import unittest
from live.injury_adjust import confirmed_out,estimate

class InjuryAdjustmentTests(unittest.TestCase):
    def test_uncertain_is_not_out(self):
        for s in ("Questionable","Doubtful","Day-To-Day","Probable"):
            self.assertFalse(confirmed_out(s))
        self.assertTrue(confirmed_out("Out"))
        self.assertTrue(confirmed_out("Injured Reserve"))
    def test_no_evidence_does_not_change_score(self):
        result=estimate("PHI",[{"player":"Jalen Hurts","position":"QB","status":"Out"}],[],[],8)
        self.assertEqual(result["points"],0)
        self.assertEqual(result["status"],"insufficient_verified_player_splits")
    def test_supported_qb_split(self):
        schedules=[]
        rows=[]
        for w,score in enumerate((28,30,14,16),1):
            schedules.append({"week":w,"game_type":"REG","home_team":"PHI","away_team":"DAL","home_score":score,"away_score":10})
            if w<=2:
                rows.append({"week":w,"team":"PHI","player_display_name":"Jalen Hurts","attempts":25,"carries":5,"targets":0})
        result=estimate("PHI",[{"player":"Jalen Hurts","position":"QB","status":"Out"}],rows,schedules,5)
        self.assertEqual(result["status"],"experimental_qb_split")
        self.assertLess(result["points"],0)
        self.assertGreaterEqual(result["points"],-6)

if __name__=="__main__":unittest.main()
