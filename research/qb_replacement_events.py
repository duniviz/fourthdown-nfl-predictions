#!/usr/bin/env python3
"""Retrospective QB replacement event audit. NOT pregame prediction features.

The starting QB in a completed-game schedule is a postgame-confirmed label.
Never pass target-game starter IDs into a predictive model.
"""
import argparse,csv,json
from pathlib import Path
from collections import defaultdict,Counter
from player_impact_research import load
from audit_historical_injuries import normalized_team
from qb_injury_interaction import qb_injury_reports
from qb_efficiency_challenger import read_qb_stats

def prior_leader(qbs,year,week,team):
 attempts=Counter()
 for w in range(max(1,week-5),week):
  for pid,att,epa in qbs.get((year,w,team),[]):
   attempts[pid]+=att
 return attempts.most_common(1)[0][0] if attempts else None

def audit(games,qbs,injury,coverage):
 cols=("home_qb_id","away_qb_id")
 if not games or not all(k in games[0] for k in cols):
  raise ValueError("Schedule lacks home_qb_id/away_qb_id: cannot verify actual QB starters")
 events=[];counts=Counter();history=defaultdict(list)
 for g in games:
  y,w=g["season"],g["week"]
  for side in ("home","away"):
   team=normalized_team(g[side+"_team"])
   actual=(g.get(side+"_qb_id") or "").strip()
   prior=prior_leader(qbs,y,w,team)
   if not actual or not prior:counts["missing_identity_or_prior"]+=1;continue
   counts["starter_observed"]+=1
   if actual==prior:continue
   counts["retrospective_changes"]+=1
   report_flag=bool(injury.get((y,w,team)))
   if report_flag:counts["changes_with_any_qb_out_doubtful_report"]+=1
   # This field is a retrospective event label, NEVER a pregame feature.
   events.append({"season":y,"week":w,"team":team,"actual_starter_id":actual,
    "prior_five_week_attempts_leader_id":prior,"qb_out_or_doubtful_report":report_flag,
    "team_points":g[side+"_score"],"opponent_points":g[("away" if side=="home" else "home")+"_score"]})
 return {"status":"RETROSPECTIVE_QB_STARTER_CHANGE_AUDIT_ONLY",
  "production_modified":False,"promotion_eligible":False,
  "verified_actual_starter_changes":counts["retrospective_changes"],
  "verified_pregame_starter_changes":0,"verified_injury_caused_starter_changes":0,
  "qb_report_corroborated_events":counts["changes_with_any_qb_out_doubtful_report"],
  "games_with_starter_id":counts["starter_observed"],
  "limitation":"Actual QB starter ID is known retrospectively, not necessarily before kickoff. Any team QB injury designation may refer to a different QB. These are not verified injury-caused replacements. Do not use actual starter as a target-game model feature.",
  "events":events}

def main():
 p=argparse.ArgumentParser();p.add_argument("--schedule",required=True,type=Path);p.add_argument("--qb-stats",required=True,type=Path,nargs="+");p.add_argument("--injuries",required=True,type=Path,nargs="+");p.add_argument("--output",required=True,type=Path)
 a=p.parse_args();inj,coverage=qb_injury_reports(a.injuries)
 report=audit(load(a.schedule),read_qb_stats(a.qb_stats),inj,coverage)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps({k:v for k,v in report.items() if k!="events"},indent=2))
if __name__=="__main__":main()
