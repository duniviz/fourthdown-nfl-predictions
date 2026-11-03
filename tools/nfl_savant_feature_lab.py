#!/usr/bin/env python3
"""Research-only NFL Savant-style situational feature availability and walk-forward evaluation.
No claims of play-by-play, air yards, snaps or pressure when columns are absent.
"""
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path
from project_player_yards import project

def num(v):
 try:
  n=float(v)
  return n if math.isfinite(n) and n>=0 else None
 except (ValueError,TypeError):return None
def metric(errors):
 n=len(errors)
 return {"samples":n,"mae":round(sum(abs(e) for e in errors)/n,2),"rmse":round(math.sqrt(sum(e*e for e in errors)/n),2)} if n else {"samples":0,"mae":None,"rmse":None}
FEATURES={"opportunity":["attempts","carries","targets"],"matchup":["opponent_team","passing_yards","rushing_yards","receiving_yards"],"scoring":["team_score","opponent_score"],"play_by_play":["air_yards","routes_run","snap_share","pressure_rate","red_zone_plays","explosive_plays"]}
def evaluate(rows,season,holdout_weeks=4):
 headers=set().union(*(r.keys() for r in rows)) if rows else set()
 available={group:{field:field in headers and any(r.get(field) not in (None,"") for r in rows) for field in fields} for group,fields in FEATURES.items()}
 history=defaultdict(list);actual=defaultdict(dict);weeks=set()
 for row in rows:
  try:
   week=int(row["week"])
   if int(row["season"])!=season or row.get("season_type","REG")!="REG" or not 1<=week<=18:continue
  except (KeyError,ValueError,TypeError):continue
  pid=row.get("player_id") or row.get("gsis_id")
  if not pid:continue
  weeks.add(week);history[pid].append((week,row));actual[week][pid]=row
 weeks=sorted(weeks)
 if len(weeks)<8:return {"status":"insufficient_completed_weeks","season":season,"feature_availability":available,"production_change_approved":False}
 cutoff=weeks[-holdout_weeks]
 errors={part:{market:{variant:[] for variant in ("baseline","opportunity_rate","recent_usage")} for market in ("passing_yards","rushing_yards","receiving_yards")} for part in ("development","holdout")}
 opportunities={"passing_yards":"attempts","rushing_yards":"carries","receiving_yards":"targets"}
 for week in weeks:
  if week<4:continue
  part="holdout" if week>=cutoff else "development"
  for forecast in project(rows,season,week):
   market=forecast["market"];pid=forecast["player_id"];target=actual[week].get(pid)
   observed=num(target.get(market)) if target else None
   if observed is None:continue
   prior=sorted((w,r) for w,r in history[pid] if w<week)
   valid=[(num(r.get(opportunities[market])),num(r.get(market))) for _,r in prior]
   valid=[(o,y) for o,y in valid if o is not None and y is not None and o>0]
   if len(valid)<3:continue
   recent=valid[-5:];base=float(forecast["projected_yards"])
   usage=.65*sum(o for o,y in recent)/len(recent)+.35*sum(o for o,y in valid)/len(valid)
   efficiency=.65*sum(y for o,y in recent)/sum(o for o,y in recent)+.35*sum(y for o,y in valid)/sum(o for o,y in valid)
   preds={"baseline":base,"opportunity_rate":usage*efficiency,"recent_usage":sum(y for o,y in recent)/len(recent)}
   for name,pred in preds.items():errors[part][market][name].append(pred-observed)
 results={p:{m:{v:metric(e) for v,e in variants.items()} for m,variants in markets.items()} for p,markets in errors.items()}
 candidates=[]
 for market in opportunities:
  for variant in ("opportunity_rate","recent_usage"):
   dev=results["development"][market];hold=results["holdout"][market]
   if dev["baseline"]["samples"]>=30 and hold["baseline"]["samples"]>=20 and all(dev[variant][k]<dev["baseline"][k] and hold[variant][k]<hold["baseline"][k] for k in ("mae","rmse")):candidates.append({"market":market,"variant":variant})
 return {"status":"research_only","season":season,"holdout_weeks":[w for w in weeks if w>=cutoff],"feature_availability":available,"results":results,"candidate_improvements":candidates,"production_change_approved":False,
 "limitations":["This first-pass test uses nflverse weekly stats, not NFL Savant play-by-play; no play-by-play signals are claimed.",
 "Air yards, snap share, pressure, red-zone and explosive-play features require separate historical pregame-safe data ingestion.",
 "Only previously observed players are evaluated; injury availability and sportsbook profitability are not validated.",
 "All features use earlier weeks only; future games are never included in a prediction.",
 "Do not promote without independent cross-season replication."]}
def main():
 p=argparse.ArgumentParser();p.add_argument("--weekly-csv",type=Path,required=True);p.add_argument("--season",type=int,required=True);p.add_argument("--output",type=Path,required=True)
 a=p.parse_args()
 with a.weekly_csv.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
 result=evaluate(rows,a.season);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n")
 print("NFL Savant-style feature audit:",{"season":a.season,"status":result["status"],"candidates":result.get("candidate_improvements",[]),"production_changed":False})
if __name__=="__main__":main()
