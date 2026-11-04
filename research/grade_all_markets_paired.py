#!/usr/bin/env python3
"""Weekly pairwise grading across ALL frozen player and game markets.

No retrospective forecasts are accepted as live head-to-head evidence.
Every challenger gets its own exact incumbent-matched player/game sample.
"""
import json,sys
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"research"))
from same_slate_leaderboard import finite,timestamp
from join_frozen_pregame_results import norm
from grade_yardage_game_models import get_game_actuals

def grade(forecasts,actuals):
 groups=defaultdict(dict);rejected=defaultdict(int)
 for r in forecasts:
  market=norm(r.get("stat_key"))
  key=(str(r.get("game_id")),str(r.get("player_id")),market)
  kick=timestamp(r.get("kickoff_utc"));when=timestamp(r.get("predicted_at_utc"))
  pred=finite(r.get("projection"));model=str(r.get("model") or "")
  if not kick or not when or when>=kick or pred is None or not model:
   rejected["invalid_or_postkickoff"]+=1;continue
  if model in groups[key]:
   groups[key][model]=None;rejected["duplicate_model"]+=1
  else:groups[key][model]=pred
 pairs=defaultdict(list)
 for key,models in groups.items():
  actual=finite(actuals.get(key))
  if actual is None:continue
  live=models.get("live")
  if live is None:
   rejected["missing_frozen_live"]+=1;continue
  for name,pred in models.items():
   if name=="live" or pred is None:continue
   pairs[(key[2],name)].append((key[0],key[1],abs(live-actual),abs(pred-actual)))
 scores=[]
 for (market,name),rows in sorted(pairs.items()):
  n=len(rows);live=sum(x[2] for x in rows)/n;candidate=sum(x[3] for x in rows)/n
  weeks={g.split("_")[0]+"_"+g.split("_")[1] for g,*_ in rows if len(g.split("_"))>=2}
  scores.append({"market":market,"challenger":name,"matched_observations":n,
    "independent_weeks":len(weeks),"live_mae":round(live,4),"challenger_mae":round(candidate,4),
    "relative_improvement":round((live-candidate)/live,5) if live else None,
    "promotion_eligible":False})
 return {"status":"ALL_MARKETS_PAIRED_FROZEN_FORECASTS","research_only":True,
         "production_modified":False,"scores":scores,"rejected":dict(rejected)}
def main():
 data=ROOT/"data"
 forecasts=json.loads((data/"weekly-shadow-forecasts.json").read_text()).get("rows",[])
 results=json.loads((data/"player-results.json").read_text()).get("rows",[])
 actuals={}
 for r in results:
  if not r.get("player_id") or r.get("actual") is None or r.get("dnp") or r.get("played") is False:continue
  actuals[(str(r.get("game_id")),str(r["player_id"]),norm(r.get("stat_key")))]=r["actual"]
 actuals.update(get_game_actuals(forecasts))
 report=grade(forecasts,actuals)
 out=ROOT/"research/all-markets-paired-results";out.mkdir(parents=True,exist_ok=True)
 (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
 lines=["# All markets: frozen live vs challenger on identical observations","",
        "Includes all available archived completed weeks, not hindsight backfills.","",
        "| Market | Challenger | Matched observations | Weeks | Live MAE | Challenger MAE | Gain |",
        "|---|---|---:|---:|---:|---:|---:|"]
 for x in report["scores"]:
  gain="—" if x["relative_improvement"] is None else f'{100*x["relative_improvement"]:.2f}%'
  lines.append(f'| {x["market"]} | {x["challenger"]} | {x["matched_observations"]} | {x["independent_weeks"]} | {x["live_mae"]} | {x["challenger_mae"]} | {gain} |')
 if not report["scores"]:lines.append("Awaiting matched frozen forecasts and verified final results.")
 lines+=["","Research only; no production auto-deployment. Historical games without frozen live forecasts are training/backtest data, not direct live comparisons."]
 (out/"RESULTS.md").write_text("\n".join(lines)+"\n")
 print("\n".join(lines))
if __name__=="__main__":main()
