#!/usr/bin/env python3
"""GB–CAR October 29, 2026 release regression: reject inflated postgame reconstructions."""
import json, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
GAME="2026_08_CAR_GB"
class GBPanthersPregameTest(unittest.TestCase):
 def test_historical_results_are_not_valid_pregame_evidence(self):
  data=json.loads((ROOT/"data/player-results.json").read_text())
  rows=[r for r in data.get("rows",[]) if r.get("game_id")==GAME]
  self.assertTrue(rows,"GB–CAR historical actuals must be present")
  young=next(r for r in rows if r.get("player")=="Bryce Young" and r.get("stat_key")=="passing_yards")
  self.assertEqual(young["actual"],209)
  self.assertGreater(young["projection"],1000,"Regression fixture should expose inflated historical projection")
 def test_no_retroactive_snapshot_from_postgame_rows(self):
  snapshots=json.loads((ROOT/"data/pregame-snapshots.json").read_text()).get("records",[])
  for row in snapshots:
   if row.get("game_id")!=GAME:continue
   self.assertLess(row["captured_at"],row["kickoff"])
   if row.get("dk_line") is not None:
    self.assertTrue(row.get("dk_captured_at"),"DK line must have source timestamp")
    self.assertLess(row["dk_captured_at"],row["kickoff"])
 def test_actuals_not_used_as_projection(self):
  data=json.loads((ROOT/"data/player-results.json").read_text())
  snapshots=json.loads((ROOT/"data/pregame-snapshots.json").read_text()).get("records",[])
  by_key={(str(r.get("game_id")),str(r.get("player_id")),str(r.get("market"))):r for r in snapshots}
  for row in data.get("rows",[]):
   if row.get("game_id")!=GAME:continue
   key=(str(row["game_id"]),str(row["player_id"]),str(row["market"]))
   if key not in by_key:continue
   self.assertNotEqual(by_key[key].get("captured_at"),data.get("generated_at_utc"))
if __name__=="__main__":unittest.main()
