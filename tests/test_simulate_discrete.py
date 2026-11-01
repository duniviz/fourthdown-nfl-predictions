"""Regression tests for discrete NFL player-prop simulation markets."""
import random
import unittest
from live.simulate import DRAWS, compact_draws, player_draws, simulate_games

class PlayerDistributionTests(unittest.TestCase):
    def test_game_cover_probabilities_and_pushes(self):
        game={"game_id":"2026_08_ARI_DAL","home":"DAL","away":"ARI","kickoff_utc":"2026-11-01T18:00:00Z","projected_home_score":27,"projected_away_score":20}
        odds=[{"bookmaker":"draftkings","home":"DAL","away":"ARI","commence_time":"2026-11-01T18:00:00Z","home_spread":-7,"total":47.5}]
        row=simulate_games([game],odds)[0]
        self.assertEqual(row["dk_total"],47.5)
        self.assertEqual(row["dk_home_spread"],-7)
        self.assertAlmostEqual(row["over_cover_pct"]+row["under_cover_pct"]+row["total_push_pct"],100,delta=.2)
        self.assertAlmostEqual(row["home_cover_pct"]+row["away_cover_pct"]+row["spread_push_pct"],100,delta=.2)
        self.assertNotIn("dk_total",simulate_games([game],[{**odds[0],"away":"NYG"}])[0])

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
