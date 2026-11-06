#!/usr/bin/env python3
"""Audit historical nflverse weekly injury-report coverage.

This is NOT a point-impact model. Weekly injury reports lack per-row publication
timestamps and do not confirm starting replacements. Never treat them as a
verified pre-kickoff snapshot or infer absence from postgame box scores.
"""
import argparse,csv,json
from collections import Counter,defaultdict
from pathlib import Path
YEARS=tuple(range(2020,2026))
GROUPS={"QB":"QB","WR":"WR","RB":"RB","OL":"OL","C":"OL","G":"OL","T":"OL",
        "LT":"OL","RT":"OL","LG":"OL","RG":"OL","OT":"OL","OG":"OL",
        "DE":"Defense","DT":"Defense","DL":"Defense","EDGE":"Defense","LB":"Defense",
        "ILB":"Defense","OLB":"Defense","CB":"Defense","S":"Defense","FS":"Defense","SS":"Defense","DB":"Defense"}
ALIASES={"JAC":"JAX","WAS":"WSH","LA":"LAR"}
def normalized_team(s):
 s=str(s or "").strip().upper()
 return ALIASES.get(s,s)
def audit(path):
 coverage=defaultdict(set);out=Counter();all_reports=Counter();statuses=Counter();unmapped=Counter()
 with path.open(newline="",encoding="utf-8-sig") as f:
  reader=csv.DictReader(f)
  required={"season","week","team","position"}
  if not required.issubset(set(reader.fieldnames or [])):raise ValueError("Missing required injury-report columns: "+str(sorted(required-set(reader.fieldnames or []))))
  if not ({"report_status","game_status"} & set(reader.fieldnames or [])):raise ValueError("Missing report_status/game_status; cannot identify injury designation")
  for r in reader:
   try:year=int(r["season"]);week=int(r["week"])
   except (ValueError,TypeError):continue
   if year not in YEARS or not 1<=week<=18:continue
   if r.get("game_type") and r["game_type"]!="REG":continue
   team=normalized_team(r["team"]);pos=str(r.get("position") or "").upper().strip()
   group=GROUPS.get(pos)
   if not group:
    unmapped[pos]+=1
    continue
   status=str(r.get("report_status") or r.get("game_status") or "").strip().lower()
   coverage[year].add((week,team))
   all_reports[(year,group)]+=1
   statuses[status or "not designated"]+=1
   if status in ("out","doubtful"):out[(year,group)]+=1
 return {"source":"nflverse weekly injury report CSV","scope":"2020-2025 REG",
         "status":"HISTORICAL_WEEKLY_REPORT_AUDIT_ONLY","verified_pregame_injury_games":0,
         "replacement_starters_verified":0,"production_modified":False,
         "limitations":["Weekly injury report is not a timestamped pre-kickoff snapshot.",
                        "An Out/Doubtful designation is a reported status, not proof of game absence.",
                        "Players missing from injury reports are not necessarily healthy.",
                        "Replacement starter and player value are not established by this file.",
                        "No player-impact adjustment or predictive lift is claimed."],
         "team_weeks_with_reports":{str(y):len(coverage[y]) for y in YEARS},
         "reported_players":{str(y):{g:all_reports[(y,g)] for g in ("QB","WR","RB","OL","Defense")} for y in YEARS},
         "out_or_doubtful_designations":{str(y):{g:out[(y,g)] for g in ("QB","WR","RB","OL","Defense")} for y in YEARS},
         "status_counts":dict(statuses),"unmapped_positions":dict(unmapped)}
def main():
 p=argparse.ArgumentParser();p.add_argument("--injuries",required=True,type=Path,nargs="+");p.add_argument("--output",required=True,type=Path);a=p.parse_args()
 results=[audit(path) for path in a.injuries]
 merged={"status":"HISTORICAL_WEEKLY_REPORT_AUDIT_ONLY","production_modified":False,
         "verified_pregame_injury_games":0,"replacement_starters_verified":0,
         "sources":results}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(merged,indent=2)+"\n")
 print(json.dumps(merged,indent=2))
if __name__=="__main__":main()
