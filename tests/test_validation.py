import unittest
from backtest.validate import evaluate

class ValidationTests(unittest.TestCase):
    def test_future_leakage_and_baselines(self):
        schedules=[]
        epa=[]
        for w in range(1,7):
            schedules.append({"season":2025,"week":w,"game_id":f"g{w}","game_type":"REG","home_team":"H","away_team":"A","home_score":27,"away_score":17,"spread_line":3.5})
            for team,off,defn in [("H",0.12,-0.05),("A",-0.05,0.1)]:
                epa.append({"season":2025,"week":w,"team":team,"offense_epa":off,"defense_epa":defn})
        result=evaluate(schedules,epa)
        self.assertTrue(result["future_data_perturbation_passed"])
        self.assertEqual(result["v2_winners"]["games"],3)
        self.assertEqual(result["market_favorite_baseline"]["games"],3)

if __name__=="__main__":
    unittest.main()
