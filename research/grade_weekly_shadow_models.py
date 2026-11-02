#!/usr/bin/env python3
"""Grade frozen shadow models only against exact verified player results."""
import json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"research"))
from same_slate_leaderboard import compare
from join_frozen_pregame_results import norm
def main():
 data=ROOT/"data";archive=json.loads((data/"weekly-shadow-forecasts.json").read_text()).get("rows",[])
 results=json.loads((data/"player-results.json").read_text()).get("rows",[])
 actuals={}
 for r in results:
  if not r.get("player_id") or r.get("actual") is None or r.get("dnp") or r.get("played") is False:continue
  key=(str(r.get("game_id")),str(r["player_id"]),norm(r.get("stat_key")))
  actuals[key]=r["actual"]
 rows=[]
 for r in archive:
  key=(str(r["game_id"]),str(r["player_id"]),norm(r["stat_key"]))
  if key in actuals:rows.append(dict(r,actual=actuals[key]))
 # Require identical ten-model coverage for each graded player/game/market.
 from collections import defaultdict
 grouped=defaultdict(list)
 for row in rows:
  grouped[(row["game_id"],row["player_id"],norm(row["stat_key"]))].append(row)
 expected={"live","baseline","workload","matchup","recent_form","baseline_workload_blend","workload_matchup_blend","baseline_matchup_blend","recent_matchup_blend","four_way_blend"}
 complete=[r for group in grouped.values() if len(group)==len(expected) and {r["model"] for r in group}==expected for r in group]
 report=compare(complete)
 report["coverage"]={"frozen_forecasts":len(archive),"verified_forecasts":len(rows),"complete_player_game_markets":len(complete)//len(expected),"incomplete_player_game_markets":len(grouped)-len(complete)//len(expected)}
 report["status"]="COMPLETE" if report["matched_slate_records"] else ("WAITING_FOR_FINAL_STATS" if archive else "WAITING_FOR_PREGAME_CAPTURE")
 out=ROOT/"research"/"weekly-shadow-results";out.mkdir(parents=True,exist_ok=True)
 (out/"leaderboard.json").write_text(json.dumps(report,indent=2)+"\n")
 lines=["# Weekly shadow model comparison","",f"Status: {report['status']}","",f"Matched player-game-markets: {report['matched_slate_records']}","",
 "| Market | Model | Samples | MAE | RMSE | DK sample | DK hit % |","|---|---|---:|---:|---:|---:|---:|"]
 for r in report["metrics"]:
  rate="—" if r["dk_hit_rate"] is None else f'{r["dk_hit_rate"]*100:.1f}%'
  lines.append(f'| {r["market"]} | {r["model"]} | {r["n"]} | {r["mae"]} | {r["rmse"]} | {r["dk_n"]} | {rate} |')
 if not report["matched_slate_records"]:lines+=["","Pending: no verified final results match frozen shadow forecasts yet."]
 lines+=["","Research only. These are live-input variants, not exact historical V3 forecasts. No automatic promotion."]
 (out/"RESULTS.md").write_text("\n".join(lines)+"\n")
 print("\n".join(lines))
if __name__=="__main__":main()
