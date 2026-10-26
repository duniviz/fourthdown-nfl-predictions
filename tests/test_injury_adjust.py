import unittest
from live.injury_adjust import confirmed_out,estimate

class InjuryAdjustmentTests(unittest.TestCase):
    def test_uncertain_is_not_out(self):
        for status in ("Questionable","Doubtful","Day-To-Day","Probable"):
            self.assertFalse(confirmed_out(status))
        for status in ("Out","Injured Reserve","IR"):
            self.assertTrue(confirmed_out(status))
    def test_no_evidence_does_not_change_score(self):
        result=estimate("PHI",[{"player":"Jalen Hurts","position":"QB","status":"Out"}],[],[],8)
        self.assertEqual(result["points"],0)
    def test_already_reflected_absence_has_small_adjustment(self):
        games=[];rows=[]
        for week in range(1,7):
            games.append({"week":week,"game_type":"REG","home_team":"PHI","away_team":"DAL","home_score":20,"away_score":17})
            name="Jalen Hurts" if week<=2 else "Tanner McKee"
            rows.append({"week":week,"team":"PHI","position":"QB","player_display_name":name,
                         "attempts":25,"passing_yards":250 if week<=2 else 160,
                         "passing_tds":1,"interceptions":0,"rushing_yards":0})
        result=estimate("PHI",[{"player":"Jalen Hurts","position":"QB","status":"Out"}],rows,games,7)
        self.assertEqual(result["status"],"experimental_qb_baseline_adjustment")
        self.assertLessEqual(abs(result["points"]),2)
        self.assertLess(result["points"],0)
    def test_other_positions_are_tracked_not_guessed(self):
        result=estimate("PHI",[{"player":"A Lineman","position":"OT","status":"Out"}],[],[],8)
        self.assertEqual(result["points"],0)
        self.assertEqual(len(result["unmodeled_injuries"]),1)
if __name__=="__main__":unittest.main()
