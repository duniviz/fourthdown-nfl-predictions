import csv,importlib.util,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("audit",ROOT/"research"/"audit_historical_injuries.py")
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
class HistoricalInjuryAuditTests(unittest.TestCase):
 def test_position_mapping_and_missing_timestamps_fail_closed(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"injuries.csv"
   with p.open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["season","week","team","position","report_status","game_type"])
    w.writeheader()
    for pos,status in [("QB","Out"),("WR","Questionable"),("RB","Doubtful"),("T","Out"),("CB","Out")]:
     w.writerow(dict(season=2025,week=9,team="JAC",position=pos,report_status=status,game_type="REG"))
   a=audit.audit(p)
   self.assertEqual(a["team_weeks_with_reports"]["2025"],1)
   self.assertEqual(a["out_or_doubtful_designations"]["2025"],{"QB":1,"WR":0,"RB":1,"OL":1,"Defense":1})
   self.assertEqual(a["verified_pregame_injury_games"],0)
   self.assertEqual(a["replacement_starters_verified"],0)
 def test_missing_status_column_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"injuries.csv";p.write_text("season,week,team,position\\n2025,1,BAL,QB\\n")
   with self.assertRaises(ValueError):audit.audit(p)
if __name__=="__main__":unittest.main()
