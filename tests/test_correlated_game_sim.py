import unittest
from tools.correlated_game_sim import simulate

HOME={"team":"HOME","points":24}
AWAY={"team":"AWAY","points":21}
PLAYERS=[{"id":"qb","team":"HOME","market":"passing_yards","mean":250,"line":249.5},
         {"id":"wr","team":"HOME","market":"receiving_yards","mean":70,"line":69.5},
         {"id":"rb","team":"AWAY","market":"rushing_yards","mean":85}]

class SimulationTests(unittest.TestCase):
    def test_reproducible_and_bounded(self):
        a=simulate(HOME,AWAY,PLAYERS,iterations=300,seed=123)
        self.assertEqual(a,simulate(HOME,AWAY,PLAYERS,iterations=300,seed=123))
        self.assertTrue(0<=a["home_win_probability"]<=1)
        self.assertTrue(a["research_only"])
        self.assertFalse(a["calibrated"])
        for p in a["players"]:
            self.assertLessEqual(p["p10"],p["p50"])
            self.assertLessEqual(p["p50"],p["p90"])
    def test_validation(self):
        with self.assertRaises(ValueError):
            simulate(HOME,HOME)
        with self.assertRaises(ValueError):
            simulate(HOME,AWAY,iterations=10)
        with self.assertRaises(ValueError):
            simulate(HOME,AWAY,[{"id":"x","team":"OTHER","market":"rushing_yards","mean":2}])
if __name__=="__main__":unittest.main()
