import csv
import tempfile
import unittest
from pathlib import Path
from tools.research_bias_challenger import evaluate

FIELDS=["season","week","player_id","market","actual","old","new"]
def write(path,rows):
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
def row(season,week,player,actual=100,new=90):
    return dict(season=season,week=week,player_id=player,market="receiving_yards",actual=actual,old=85,new=new)
class ChallengerTests(unittest.TestCase):
    def test_frozen_train_and_holdout(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"sample.csv"
            write(p,[row(2024,1,i) for i in range(40)]+[row(2025,1,i,actual=80) for i in range(40)])
            r=evaluate(p);m=r["markets"]["receiving_yards"]
            self.assertEqual(r["holdout_season"],2025)
            self.assertEqual(m["train_n"],40)
            self.assertEqual(m["holdout_n"],40)
            self.assertGreater(m["frozen_offset"],0)
            self.assertEqual(m["holdout_weeks"],1)
            self.assertEqual(len(m["weekly_diagnostics"]),1)
            self.assertEqual(m["weekly_diagnostics"][0]["samples"],40)
            self.assertFalse(m["eligible_for_promotion"])
            self.assertFalse(r["production_changed"])
            self.assertFalse(r["production_equivalence_verified"])
    def test_multiple_holdout_weeks_reported_without_promotion(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"sample.csv"
            write(p,[row(2024,1,i) for i in range(40)]+[row(2025,w,i,actual=80 if w==1 else 110) for w in (1,2) for i in range(40)])
            m=evaluate(p)["markets"]["receiving_yards"]
            self.assertEqual(m["holdout_weeks"],2)
            self.assertEqual([x["week"] for x in m["weekly_diagnostics"]],[1,2])
            self.assertLessEqual(m["weeks_improved"],2)
            self.assertFalse(m["eligible_for_promotion"])
    def test_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"sample.csv";write(p,[row(2024,1,"p"),row(2024,1,"p"),row(2025,1,"p")])
            with self.assertRaisesRegex(ValueError,"Duplicate"):evaluate(p)
    def test_single_season_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"sample.csv";write(p,[row(2025,1,"p")])
            with self.assertRaisesRegex(ValueError,"two chronological"):evaluate(p)
if __name__=="__main__":unittest.main()
