import unittest
from datetime import datetime,timezone
from tools.match_dk_player_lines import match

class MatchingTests(unittest.TestCase):
    def test_unique_exact_market_match(self):
        now=datetime.now(timezone.utc)
        p=[{"player_id":"abc","player_name":"Test Player","team":"GB","opponent":"CHI","market":"rushing_yards","projected_yards":65}]
        q={"bookmaker":"draftkings","rows":[{"player":"Test Player","home_team":"Green Bay Packers","away_team":"Chicago Bears","market_key":"player_rush_yds","line":59.5,"last_update":now.isoformat()}]}
        rows,counts,diag=match(p,q,now)
        self.assertEqual(counts["matched"],1)
        self.assertEqual(diag["market_inventory"]["rushing_yards"],1)
        self.assertEqual(rows[0]["recommendation_eligible"],False)
    def test_wrong_matchup_not_matched(self):
        now=datetime.now(timezone.utc)
        p=[{"player_id":"abc","player_name":"Test Player","team":"GB","opponent":"CHI","market":"rushing_yards","projected_yards":65}]
        q={"bookmaker":"draftkings","rows":[{"player":"Test Player","home_team":"Green Bay Packers","away_team":"Detroit Lions","market_key":"player_rush_yds","line":59.5,"last_update":now.isoformat()}]}
        rows,counts,_=match(p,q,now)
        self.assertEqual(counts["missing"],1)
        self.assertIsNone(rows[0]["dk_line"])
if __name__=="__main__":unittest.main()
