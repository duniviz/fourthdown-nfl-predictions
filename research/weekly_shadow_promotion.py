#!/usr/bin/env python3
"""Automatic, fail-closed weekly champion/challenger evaluation.

Promotes *shadow research champion* only. Production selection is deliberately
blocked until a deployable versioned inference artifact and tested rollback exist.
Every candidate is evaluated against the incumbent on identical frozen games.
"""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MIN_GAMES=100
MIN_WEEKS=3
GAIN=.05

def choose(report,previous=None):
 previous=previous or {}
 decisions={}
 for item in report.get("comparisons",[]):
  market=item["market"];name=item["challenger"]
  gain=item.get("relative_improvement")
  passed=(item.get("matched_games",0)>=MIN_GAMES and
          item.get("independent_weeks",0)>=MIN_WEEKS and
          gain is not None and gain>=GAIN)
  if passed and (market not in decisions or gain>decisions[market]["relative_improvement"]):
   decisions[market]={"candidate":name,"relative_improvement":gain,
                      "matched_games":item["matched_games"],"independent_weeks":item["independent_weeks"],
                      "action":"shadow_promotion_eligible"}
 for market in ("game_margin_home","game_total"):
  decisions.setdefault(market,{"action":"retain","reason":"No candidate met 5% gain over >=100 identical games and >=3 weeks"})
 return {"policy":{"min_matched_games":MIN_GAMES,"min_weeks":MIN_WEEKS,"min_relative_mae_gain":GAIN},
         "decisions":decisions,"production_auto_promotion_enabled":False,
         "reason":"No versioned deployable inference artifact or tested production rollback. Never infer deployability from a leaderboard.",
         "previous_shadow_decisions":previous.get("decisions",{})}
def main():
 report=json.loads((ROOT/"research/paired-game-results/report.json").read_text())
 path=ROOT/"research/paired-game-results/shadow-decisions.json"
 previous=json.loads(path.read_text()) if path.exists() else {}
 decision=choose(report,previous)
 path.write_text(json.dumps(decision,indent=2)+"\n")
 print(json.dumps(decision,indent=2))
if __name__=="__main__":main()
