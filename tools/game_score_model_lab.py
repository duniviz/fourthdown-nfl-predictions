#!/usr/bin/env python3
"""Research-only, chronological game score/total/margin model comparison."""
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path
from build_team_baseline import build

VARIANTS=("baseline","recent_form","less_shrinkage","home_advantage_zero","home_advantage_three","combined")
def metric(errors):
 n=len(errors)
 return {"samples":n,"mae":round(sum(abs(x) for x in errors)/n,2),"rmse":round(math.sqrt(sum(x*x for x in errors)/n),2),"bias":round(sum(errors)/n,2)} if n else {"samples":0,"mae":None,"rmse":None,"bias":None}
def evaluate(rows,season,holdout_weeks=4):
 games=[]
 for r in rows:
  try:
   if int(r["season"])!=season or r.get("game_type","REG")!="REG":continue
   week=int(r["week"]);home=r["home_team"];away=r["away_team"]
   hs=float(r["home_score"]);aw=float(r["away_score"])
   if not home or not away or home==away or not all(math.isfinite(x) and 0<=x<=100 for x in (hs,aw)):continue
   if not 1<=week<=18:continue
   games.append((week,home,away,hs,aw))
  except (KeyError,ValueError,TypeError):continue
 games.sort()
 weeks=sorted(set(x[0] for x in games))
 if len(weeks)<8:return {"status":"insufficient_completed_weeks","season":season,"weeks":len(weeks),"production_change_approved":False}
 cutoff=weeks[-holdout_weeks] if len(weeks)>=holdout_weeks else weeks[-1]
 errors={part:{v:{k:[] for k in ("home_score","away_score","total","home_margin")} for v in VARIANTS} for part in ("development","holdout")}
 for week in weeks:
  if week<4:continue
  past=[g for g in games if g[0]<week]
  if not past:continue
  base=build(past)["teams"]
  last=defaultdict(list)
  for w,h,a,hs,aw in past:
   last[h].append((w,hs,aw));last[a].append((w,aw,hs))
  for w,h,a,hs,aw in (g for g in games if g[0]==week):
   if h not in base or a not in base or not base[h]["eligible"] or not base[a]["eligible"]:continue
   hb,ab=base[h],base[a]
   def pred(hfor,hagainst,afor,aagainst,adv):
    return (max(0,.5*(hfor+aagainst)+adv),max(0,.5*(afor+hagainst)-adv))
   normal=pred(hb["points_for"],hb["points_against"],ab["points_for"],ab["points_against"],1)
   def recent(team,key,original):
    values=sorted(last[team])[-3:]
    return .5*original+.5*sum(x[key] for x in values)/len(values) if values else original
   rf=pred(recent(h,1,hb["points_for"]),recent(h,2,hb["points_against"]),recent(a,1,ab["points_for"]),recent(a,2,ab["points_against"]),1)
   def less(team,key,original):
    values=last[team]
    avg=sum(x[key] for x in values)/len(values)
    return .5*original+.5*avg
   ls=pred(less(h,1,hb["points_for"]),less(h,2,hb["points_against"]),less(a,1,ab["points_for"]),less(a,2,ab["points_against"]),1)
   variants={"baseline":normal,"recent_form":rf,"less_shrinkage":ls,
    "home_advantage_zero":pred(hb["points_for"],hb["points_against"],ab["points_for"],ab["points_against"],0),
    "home_advantage_three":pred(hb["points_for"],hb["points_against"],ab["points_for"],ab["points_against"],3),
    "combined":pred(recent(h,1,hb["points_for"]),recent(h,2,hb["points_against"]),recent(a,1,ab["points_for"]),recent(a,2,ab["points_against"]),0)}
   part="holdout" if week>=cutoff else "development"
   for name,(ph,pa) in variants.items():
    for k,e in (("home_score",ph-hs),("away_score",pa-aw),("total",ph+pa-hs-aw),("home_margin",ph-pa-hs+aw)):
     errors[part][name][k].append(e)
 results={part:{name:{k:metric(e) for k,e in markets.items()} for name,markets in values.items()} for part,values in errors.items()}
 candidates=[]
 for name in VARIANTS[1:]:
  if all(results[part][name][k]["samples"]>= (20 if part=="holdout" else 50)
   and results[part][name][k]["mae"]<results[part]["baseline"][k]["mae"]
   and results[part][name][k]["rmse"]<results[part]["baseline"][k]["rmse"]
   for part in ("development","holdout") for k in ("total","home_margin")):candidates.append(name)
 return {"status":"research_only","season":season,"holdout_weeks":[w for w in weeks if w>=cutoff],
  "results":results,"candidate_improvements":candidates,"production_change_approved":False,
  "limitations":["Only completed games and strictly earlier weeks are used for every prediction.","Development and holdout are from the same season; replicate across seasons before any promotion.","Total is projected points, not a verified sportsbook over/under line.","No weather, injury or verified sportsbook inputs included.","No automatic model weight changes."]}
def main():
 p=argparse.ArgumentParser();p.add_argument("--schedule-csv",type=Path,required=True);p.add_argument("--season",type=int,required=True);p.add_argument("--output",type=Path,required=True)
 a=p.parse_args()
 with a.schedule_csv.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
 result=evaluate(rows,a.season)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n")
 print("Game score model lab:",{"season":a.season,"status":result["status"],"candidates":result.get("candidate_improvements",[]),"production_changed":False})
if __name__=="__main__":main()
