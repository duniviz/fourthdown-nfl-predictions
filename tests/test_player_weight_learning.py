import unittest
from live.player_weight_learning import evaluate

def row(week,actual,projection=100):
    return {"game_id":f"2026_{week:02d}_AAA_BBB","stat_key":"rushing_yards","actual":actual,"projection":projection}

class TestWeeklyWeightLearning(unittest.TestCase):
    def test_insufficient_data_keeps_baseline(self):
        self.assertEqual(evaluate([row(1,110)])["rushing_yards"]["weight"],0.0)
    def test_persistent_bias_can_promote(self):
        rows=[row(w,110) for w in range(1,15) for _ in range(12)]
        result=evaluate(rows)["rushing_yards"]
        self.assertGreater(result["weight"],0.0)
        self.assertEqual(result["status"],"validated")
    def test_unstable_bias_keeps_baseline(self):
        rows=[row(w,110 if w%2 else 90) for w in range(1,15) for _ in range(12)]
        self.assertEqual(evaluate(rows)["rushing_yards"]["weight"],0.0)

if __name__=="__main__": unittest.main()
