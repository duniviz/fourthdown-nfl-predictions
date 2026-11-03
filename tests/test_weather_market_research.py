import csv
import tempfile
import unittest
from pathlib import Path
from tools.weather_market_research import FIELDS,evaluate

def row(season,i,market="passing_yards",wind=20,roof="outdoor",capture="2024-09-01T16:00:00Z"):
    return dict(season=season,week=i//16+1,game_id=f"{season}_{i}",player_id="qb" if market!="game_total" else "",
        market=market,kickoff_utc="2024-09-01T17:00:00Z",forecast_captured_at_utc=capture,
        forecast_wind_mph=wind,forecast_temp_f=25,forecast_precip_pct=75,roof_status=roof,
        baseline_projection=200 if market=="passing_yards" else 45,
        actual=170 if market=="passing_yards" else 40)
def write(path,rows):
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=sorted(FIELDS));w.writeheader();w.writerows(rows)
class WeatherMarketTests(unittest.TestCase):
    def test_game_and_player_holdout_both_evaluated(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.csv"
            write(p,[row(s,i,m) for s,n in ((2024,40),(2025,30)) for i in range(n) for m in ("game_total","passing_yards")])
            r=evaluate(p)
            self.assertEqual(r["holdout_season"],2025)
            self.assertEqual(r["markets"]["game_total"]["wind_18"]["holdout_n"],30)
            self.assertEqual(r["markets"]["passing_yards"]["wind_18"]["holdout_n"],30)
            self.assertFalse(r["eligible_for_promotion"])
    def test_closed_roof_never_weather_adjusts(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.csv";write(p,[row(s,i,roof="closed") for s,n in ((2024,40),(2025,30)) for i in range(n)])
            self.assertEqual(evaluate(p)["markets"]["passing_yards"]["wind_18"]["train_n"],0)
    def test_post_kickoff_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.csv";write(p,[row(2024,0,capture="2024-09-01T18:00:00Z")])
            self.assertEqual(evaluate(p)["rejected"]["unverified_pregame"],1)
    def test_duplicate_player_market_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.csv";write(p,[row(2024,0),row(2024,0)])
            with self.assertRaisesRegex(ValueError,"Duplicate"):evaluate(p)
if __name__=="__main__":unittest.main()
