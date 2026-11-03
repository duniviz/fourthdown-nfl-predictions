#!/usr/bin/env python3
"""Research-only three-factor player prop lab: QB volume, receiver opportunity, pregame game script.
Strict prior-week inputs, chronological holdout; no automatic production changes.
"""
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path
from project_player_yards import project

VARIANTS=("baseline","qb_attempts_efficiency","receiver_target_share","pregame_game_script","combined")
def number(x,low=0,high=10000):
 try:
  v=float(x)
  return v if math.isfinite(v) and low<=v<=high else None
 except (ValueError,TypeError):return None
def average(xs):return sum(xs)/len(xs) if xs else None
def metrics(xs):
 n=len(xs)
 return {"samples":n,"mae":round(average([abs(x) for x in xs]),2),"rmse":round(math.sqrt(average([x*x for x in xs])),2),"bias":round(average(xs),2)} if n else {"samples":0,"mae":None,"rmse":None,"bias":None}
def evaluate(rows,schedule,season,holdout_weeks=4,min_games=3):
 if holdout_weeks<1:raise ValueError("Holdout must be positive")
 player=defaultdict(list);by_week=defaultdict(list);team_week=defaultdict(list)
 for row in rows:
  try:
   w=int(row["week"])
   if int(row["season"])!=season or row.get("season_type","REG")!="REG" or not 1<=w<=18:continue
  except (KeyError,ValueError,TypeError):continue
  pid=row.get("player_id") or row.get("gsis_id");team=row.get("recent_team") or row.get("team")
  if not pid or not team:continue
  player[pid].append((w,row));by_week[w].append(row);team_week[(w,team)].append(row)
 games=defaultdict(list);matchups={}
 for row in schedule:
  try:
   w=int(row["week"])
   if int(row["season"])!=season or row.get("game_type","REG")!="REG" or not 1<=w<=18:continue
  except (KeyError,ValueError,TypeError):continue
  h=row.get("home_team");a=row.get("away_team")
  if not h or not a or h==a:continue
  matchups[(w,h)]=(a,True);matchups[(w,a)]=(h,False)
  hs=number(row.get("home_score"),0,100);aw=number(row.get("away_score"),0,100)
  if hs is not None and aw is not None:
   games[w].append((h,a,hs,aw))
 weeks=sorted(games)
 if len(weeks)<8:return {"status":"insufficient_completed_weeks","season":season,"completed_weeks":len(weeks),"production_change_approved":False}
 cutoff=weeks[-holdout_weeks]
 errors={p:{v:{m:[] for m in ("passing_yards","receiving_yards")} for v in VARIANTS} for p in ("development","holdout")}
 coverage=defaultdict(int)
 for week in weeks:
  if week<4:continue
  prior_games=[g for w in weeks if w<week for g in games[w]]
  # Historical scoring strength and expected pregame margin, never actual current-week score.
  team_scores=defaultdict(list)
  for h,a,hs,aw in prior_games:
   team_scores[h].append((hs,aw));team_scores[a].append((aw,hs))
  league=average([score for vals in team_scores.values() for score,_ in vals]) or 22
  def strength(team):
   vals=team_scores.get(team,[])
   if len(vals)<3:return None
   n=len(vals);weight=n/(n+5)
   return (weight*average([v[0] for v in vals])+(1-weight)*league,
           weight*average([v[1] for v in vals])+(1-weight)*league)
  forecasts=project(rows,season,week,min_games=min_games)
  actual={(r.get("player_id") or r.get("gsis_id"),m):number(r.get(m),0,700) for r in by_week[week] for m in ("passing_yards","receiving_yards")}
  # Opportunity inputs are aggregated by team and week using ONLY prior weeks.
  team_targets=defaultdict(float)
  for (w,team),group in team_week.items():
   if w>=week:continue
   total=sum(number(r.get("targets"),0,40) or 0 for r in group)
   if total>0:team_targets[(w,team)]=total
  for f in forecasts:
   market=f["market"]
   if market not in ("passing_yards","receiving_yards"):continue
   pid=f["player_id"];team=f["team"];observed=actual.get((pid,market))
   if observed is None or (week,team) not in matchups:continue
   history=sorted([(w,row) for w,row in player[pid] if w<week],key=lambda x:x[0])
   if len(history)<min_games:continue
   base=float(f["projected_yards"])
   # QB: attempts x yards per attempt; shrink last-five volume and efficiency toward season history.
   qb=None
   if market=="passing_yards":
    valid=[(number(row.get("attempts"),0,90),number(row.get("passing_yards"),0,700)) for _,row in history]
    valid=[(a,y) for a,y in valid if a is not None and y is not None and a>0]
    if len(valid)>=min_games:
     recent=valid[-5:];a=.65*average([x[0] for x in recent])+.35*average([x[0] for x in valid])
     eff=.65*(sum(y for a,y in recent)/sum(a for a,y in recent))+.35*(sum(y for a,y in valid)/sum(a for a,y in valid))
     qb=a*eff
   # WR/TE: team target share x projected team targets x player yards per target.
   # Air yards/routes are not present in all weekly releases; do not fabricate them.
   receiver=None
   if market=="receiving_yards":
    valid=[]
    for w,row in history:
     targets=number(row.get("targets"),0,40);yards=number(row.get("receiving_yards"),0,700)
     team_total=team_targets.get((w,team))
     if targets is not None and yards is not None and team_total and targets<=team_total:valid.append((w,targets,yards,team_total))
    if len(valid)>=min_games and sum(x[1] for x in valid)>0:
     recent=valid[-5:]
     share=.65*average([x[1]/x[3] for x in recent])+.35*average([x[1]/x[3] for x in valid])
     totals=[v for (w,t),v in team_targets.items() if t==team and w<week]
     expected_targets=.65*average(totals[-5:])+.35*average(totals)
     ypt=.65*sum(x[2] for x in recent)/max(1,sum(x[1] for x in recent))+.35*sum(x[2] for x in valid)/sum(x[1] for x in valid)
     receiver=share*expected_targets*ypt
   opponent,home=matchups[(week,team)]
   own=strength(team);opp=strength(opponent)
   script=None
   if own and opp:
    projected_margin=.5*(own[0]+opp[1])-.5*(opp[0]+own[1])+(2 if home else -2)
    # Trailing projected teams modestly increase pass volume; clamp to avoid extreme extrapolation.
    script=max(.92,min(1.08,1-.003*projected_margin))
   factor=script if script is not None else 1
   opportunity=qb if market=="passing_yards" else receiver
   if opportunity is None:coverage["missing_opportunity_inputs"]+=1
   if script is None:coverage["missing_pregame_script_inputs"]+=1
   estimates={"baseline":base,"qb_attempts_efficiency":qb if market=="passing_yards" and qb is not None else base,
    "receiver_target_share":receiver if market=="receiving_yards" and receiver is not None else base,
    "pregame_game_script":base*factor,"combined":(opportunity if opportunity is not None else base)*factor}
   part="holdout" if week>=cutoff else "development"
   for name,pred in estimates.items():
    if not math.isfinite(pred):raise ValueError("Nonfinite prediction")
    errors[part][name][market].append(pred-observed)
   coverage[part]+=1
 results={part:{v:{m:metrics(xs) for m,xs in markets.items()} for v,markets in variants.items()} for part,variants in errors.items()}
 candidates=[]
 for market in ("passing_yards","receiving_yards"):
  for name in VARIANTS[1:]:
   if (market=="passing_yards" and name=="receiver_target_share") or (market=="receiving_yards" and name=="qb_attempts_efficiency"):continue
   dev=results["development"][name][market];hold=results["holdout"][name][market]
   bd=results["development"]["baseline"][market];bh=results["holdout"]["baseline"][market]
   if dev["samples"]>=30 and hold["samples"]>=20 and all(dev[k]<bd[k] and hold[k]<bh[k] for k in ("mae","rmse")):
    candidates.append({"market":market,"variant":name})
 return {"status":"research_only","season":season,"holdout_weeks":[w for w in weeks if w>=cutoff],
  "coverage":dict(coverage),"results":results,"candidate_improvements":candidates,"production_change_approved":False,
  "factors_tested":["QB attempts times yards per attempt","receiver team target share and yards per target","projected pregame scoring margin game script"],
  "limitations":["No verified routes-run or air-yards inputs in the required weekly source; those features are not claimed or fabricated.",
   "Player projections only for players with prior eligible usage and an observed result; no injury-availability validation or betting-return claims.",
   "All estimates use completed prior weeks; target-week actual outcomes are used only to grade predictions.",
   "Single-season development/holdout is exploratory; independent seasons and future weeks required before promotion.",
   "Script is estimated from prior team scoring, not current-game result or unverified sportsbook lines."]}
def main():
 p=argparse.ArgumentParser();p.add_argument("--weekly-csv",type=Path,required=True);p.add_argument("--schedule-csv",type=Path,required=True);p.add_argument("--season",type=int,required=True);p.add_argument("--output",type=Path,required=True)
 a=p.parse_args()
 with a.weekly_csv.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
 with a.schedule_csv.open(newline="",encoding="utf-8-sig") as f:schedule=list(csv.DictReader(f))
 result=evaluate(rows,schedule,a.season)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n")
 print("Three-factor player prop lab:",{"season":a.season,"status":result["status"],"candidates":result.get("candidate_improvements",[]),"production_changed":False})
if __name__=="__main__":main()
