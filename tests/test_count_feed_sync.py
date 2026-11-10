import csv
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from publish_count_prop_projections import completed_player_rows

class CompletedCountGamesTests(unittest.TestCase):
    def test_excludes_in_progress_and_wrong_game(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'games.csv'
            games=[{'season':2026,'week':9,'game_type':'REG','game_id':'finished','home_team':'A','away_team':'B','home_score':24,'away_score':17},
                   {'season':2026,'week':9,'game_type':'REG','game_id':'in_progress','home_team':'C','away_team':'D','home_score':'','away_score':''}]
            with p.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=games[0].keys());w.writeheader();w.writerows(games)
            rows=[{'season':'2026','week':'9','team':'A','game_id':'finished'},
                  {'season':'2026','week':'9','team':'C','game_id':'in_progress'},
                  {'season':'2026','week':'9','team':'A','game_id':'other'},
                  {'season':'2026','week':'9','team':'B','game_id':''}]
            kept=completed_player_rows(rows,p,2026,10)
            self.assertEqual(kept,[rows[0],rows[3]])

if __name__=='__main__': unittest.main()
