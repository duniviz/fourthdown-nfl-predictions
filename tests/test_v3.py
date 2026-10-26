import unittest
from backtest.v3 import elo_predictions, fit_logistic, predict, scores

class V3Tests(unittest.TestCase):
    def test_elo_no_same_week_leakage(self):
        rows=[
            dict(season=2025,week=1,game_id="a",home_team="H",away_team="A",home_score=24,away_score=14,game_type="REG"),
            dict(season=2025,week=2,game_id="b",home_team="H",away_team="A",home_score=20,away_score=17,game_type="REG")]
        first=elo_predictions(rows)
        rows[0]["home_score"]=0
        rows[0]["away_score"]=40
        second=elo_predictions(rows)
        self.assertEqual(first["a"],second["a"])
        self.assertNotEqual(first["b"],second["b"])

    def test_calibration_returns_probabilities(self):
        m=fit_logistic([[1,1],[-1,-1],[2,3],[-2,-3]],[1,0,1,0],iterations=100)
        self.assertGreater(predict(m,[2,3]),predict(m,[-2,-3]))
        self.assertTrue(0<predict(m,[2,3])<1)

if __name__=="__main__":unittest.main()
