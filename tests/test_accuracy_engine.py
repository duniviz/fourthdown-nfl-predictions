"""Regression tests for Accuracy Engine; synthetic data, no production changes."""
import csv
import tempfile
import unittest
from pathlib import Path
from tools.accuracy_engine import run

FIELDS=["season","week","player_id","team","market","actual","old","new"]

def make_csv(path,rows):
    with path.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

def record(season,week,player,actual=100):
    return dict(season=season,week=week,player_id=str(player),team="TEST",
                market="passing_yards",actual=actual,old=actual+10,new=actual+5)

class AccuracyEngineTests(unittest.TestCase):
    def test_chronological_holdout_and_no_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"history.csv"
            make_csv(path,[record(y,w,i) for y in (2024,2025) for w in (4,5) for i in range(20)])
            report=run(path)
            self.assertEqual(report["holdout_season"],2025)
            self.assertEqual(report["holdout_rows"],40)
            self.assertFalse(report["production_changed"])
            self.assertFalse(report["automatic_promotion"])
            self.assertFalse(report["markets"]["passing_yards"]["eligible_for_promotion"])
            self.assertFalse(report["probability_research"]["passing_yards"]["dk_calibrated"])
    def test_duplicate_row_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"history.csv"
            make_csv(path,[record(2024,4,1),record(2024,4,1),record(2025,4,1)])
            with self.assertRaisesRegex(RuntimeError,"Duplicate historical prediction"):
                run(path)
    def test_single_season_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"history.csv"
            make_csv(path,[record(2025,4,1)])
            with self.assertRaisesRegex(ValueError,"two chronological seasons"):
                run(path)
    def test_empty_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"history.csv"
            make_csv(path,[])
            with self.assertRaises(ValueError):
                run(path)

if __name__=="__main__":
    unittest.main()
