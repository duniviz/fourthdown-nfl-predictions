"""Regression tests for discrete NFL player-prop simulation markets."""
import random
import unittest
from live.simulate import DRAWS, compact_draws, player_draws

class PlayerDistributionTests(unittest.TestCase):
    def test_count_markets_are_nonnegative_integers(self):
        for key in ("attempts", "completions", "carries", "receptions"):
            draws=player_draws(random.Random(42),key,8.0,3.0)
            self.assertEqual(len(draws),DRAWS)
            self.assertTrue(all(isinstance(v,int) and v>=0 for v in draws))

    def test_touchdown_and_interception_markets_are_discrete(self):
        for key in ("passing_tds", "rushing_tds", "receiving_tds", "interceptions"):
            draws=player_draws(random.Random(42),key,0.7,0.5)
            self.assertTrue(all(isinstance(v,int) and v>=0 for v in draws))
            self.assertAlmostEqual(sum(draws)/len(draws),0.7,delta=0.05)

    def test_yardage_markets_remain_continuous(self):
        draws=player_draws(random.Random(42),"receiving_yards",65.0,25.0)
        self.assertEqual(len(draws),DRAWS)
        self.assertTrue(all(v>=0 for v in draws))
        self.assertTrue(any(not float(v).is_integer() for v in draws))

    def test_published_draws_stay_compact(self):
        draws=compact_draws(list(range(DRAWS)))
        self.assertEqual(len(draws),501)
        self.assertEqual(draws[0],0)
        self.assertEqual(draws[-1],DRAWS-1)

if __name__=="__main__":
    unittest.main()
