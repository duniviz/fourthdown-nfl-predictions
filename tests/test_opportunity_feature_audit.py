import csv
import tempfile
import unittest
from pathlib import Path
from tools.opportunity_feature_audit import audit

BASE=["season","week","player_id","market","actual","new"]
def write(path,columns,rows):
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)
class OpportunityAuditTests(unittest.TestCase):
    def test_missing_opportunity_features_cannot_train(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.csv"
            write(p,BASE,[dict(season=2024,week=1,player_id="p",market="receiving_yards",actual=60,new=50)])
            r=audit(p)
            self.assertFalse(r["markets"]["receiving_yards"]["eligible_for_opportunity_training"])
            self.assertFalse(r["trained_model"])
            self.assertFalse(r["production_changed"])
    def test_partial_feature_rows_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.csv"
            write(p,BASE+["expected_targets"],[dict(season=2024,week=1,player_id="p",market="receiving_yards",actual=60,new=50,expected_targets=7)])
            r=audit(p)
            self.assertEqual(r["markets"]["receiving_yards"]["nonempty_feature_rows"]["expected_targets"],1)
            self.assertFalse(r["markets"]["receiving_yards"]["eligible_for_opportunity_training"])
    def test_missing_required_fields_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.csv"
            write(p,["market"],[dict(market="receiving_yards")])
            with self.assertRaisesRegex(ValueError,"mandatory"):audit(p)
if __name__=="__main__":unittest.main()
