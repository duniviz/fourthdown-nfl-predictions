import csv
import tempfile
import unittest
from pathlib import Path
from tools.weather_combo_research import FIELDS,evaluate
def write(path,rows):
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=sorted(FIELDS));w.writeheader();w.writerows(rows)
def game(season,i,wind=15,temp=25,rain=10,roof="outdoor",capture="2024-09-01T16:00:00Z",kickoff="2024-09-01T17:00:00Z"):
    return dict(season=season,week=i//16+1,game_id=str(season)+"_"+str(i),kickoff_utc=kickoff,
                forecast_captured_at_utc=capture,forecast_wind_mph=wind,forecast_temp_f=temp,
                forecast_precip_pct=rain,roof_status=roof,baseline_total=45,actual_total=40)
class WeatherComboTests(unittest.TestCase):
    def test_frozen_holdout_and_no_promotion(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.csv";write(p,[game(2024,i) for i in range(40)]+[game(2025,i) for i in range(30)])
            r=evaluate(p);m=r["combinations"]["wind_and_cold"]
            self.assertEqual(r["holdout_season"],2025)
            self.assertEqual(m["train_n"],40)
            self.assertEqual(m["holdout_n"],30)
            self.assertGreater(m["mae_improvement"],0)
            self.assertFalse(r["eligible_for_promotion"])
    def test_postkickoff_forecasts_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.csv";write(p,[game(2024,1,capture="2024-09-01T18:00:00Z")])
            r=evaluate(p)
            self.assertEqual(r["rejected"]["not_verified_pregame"],1)
    def test_closed_roof_blocks_weather_effect(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.csv";write(p,[game(2024,i,roof="closed") for i in range(40)]+[game(2025,i,roof="closed") for i in range(30)])
            r=evaluate(p)
            self.assertEqual(r["combinations"]["wind_12"]["train_n"],0)
    def test_duplicate_game_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.csv";write(p,[game(2024,1),game(2024,1)])
            with self.assertRaisesRegex(ValueError,"Duplicate"):evaluate(p)
    def test_single_season_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.csv";write(p,[game(2024,i) for i in range(40)])
            self.assertEqual(evaluate(p)["status"],"insufficient_chronological_seasons")
if __name__=="__main__":unittest.main()
