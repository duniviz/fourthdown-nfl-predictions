#!/usr/bin/env python3
"""Chronological research-only player yard model/ensemble comparison."""
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path
from project_player_yards import project
M=("passing_yards","rushing_yards","receiving_yards")
V=("baseline","rolling_3","rolling_5","ewma","usage_efficiency","blend_recent_usage","blend_ewma_usage")
O={"passing_yards":"attempts","rushing_yards":"carries","receiving_yards":"targets"}
def val(x):
 try:
  n=float(x)
  return n if math.isfinite(n) and 0<=n<=700 else None
 except (ValueError,TypeError):return None
def metric(a):
 n=len(a)
 return {"samples":n,"mae":round(sum(abs(x) for x in a)/n,3),"rmse":round(math.sqrt(sum(x*x for x in a)/n),3)} if n else {"samples":0,"mae":None,"rmse":None}
def evaluate(rows,season):
 history=defaultdict(list);actual=defaultdict(dict);weeks=set()
 for r in rows:
  try:
   w=int(r["week"])
   if int(r["season"])!=season or r.get("season_type","REG")!="REG" or not 1<=w<=18:continue
  except (KeyError,TypeError,ValueError):continue
  pid=r.get("player_id") or r.get("gsis_id")
  if pid:history[pid].append((w,r));actual[w][pid]=r;weeks.add(w)
 weeks=sorted(weeks)
 if len(weeks)<8:return {"season":season,"status":"insufficient_completed_weeks","production_changed":False}
 cutoff=weeks[-4]
 errors={part:{m:{v:[] for v in V} for m in M} for part in ("development","holdout")}
 for week in weeks:
  if week<4:continue
  part="holdout" if week>=cutoff else "development"
  for f in project(rows,season,week):
   pid=f["player_id"];m=f["market"];target=actual[week].get(pid)
   y=val(target.get(m)) if target else None
   if y is None:continue
   prior=[(val(r.get(m)),val(r.get(O[m]))) for w,r in sorted(history[pid]) if w<week]
   prior=[(a,o) for a,o in prior if a is not None and o is not None]
   if len(prior)<3:continue
   ys=[a for a,o in prior];last=ys[-5:];ew=ys[0]
   for x in ys[1:]:ew=.45*x+.55*ew
   valid=[(a,o) for a,o in prior if o>0]
   usage=None
   if len(valid)>=3:
    recent=valid[-5:]
    volume=.65*sum(o for a,o in recent)/len(recent)+.35*sum(o for a,o in valid)/len(valid)
    efficiency=.65*sum(a for a,o in recent)/sum(o for a,o in recent)+.35*sum(a for a,o in valid)/sum(o for a,o in valid)
    usage=volume*efficiency
   base=float(f["projected_yards"]);rolling3=sum(ys[-3:])/3;rolling5=sum(last)/len(last)
   pred={"baseline":base,"rolling_3":rolling3,"rolling_5":rolling5,"ewma":ew,"usage_efficiency":usage,"blend_recent_usage":(.5*rolling3+.5*usage) if usage is not None else None,"blend_ewma_usage":(.5*ew+.5*usage) if usage is not None else None}
   # Only evaluate matched predictions for fair sample comparisons.
   if any(x is None for x in pred.values()):continue
   for name,x in pred.items():errors[part][m][name].append(x-y)
 results={p:{m:{v:metric(e) for v,e in vs.items()} for m,vs in ms.items()} for p,ms in errors.items()}
 candidates=[]
 for m in M:
  for v in V[1:]:
   d=results["development"][m];h=results["holdout"][m]
   if d[v]["samples"]>=30 and h[v]["samples"]>=20 and all(t[v][k]<t["baseline"][k] for t in (d,h) for k in ("mae","rmse")):candidates.append({"market":m,"variant":v})
 return {"season":season,"status":"research_only","holdout_weeks":[w for w in weeks if w>=cutoff],"results":results,"candidate_improvements":candidates,"production_changed":False,"limitations":["Weekly stats support rolling averages, usage/efficiency, and simple blends only.","WOPR, PROE, xTD, EPA, pace, pressure and red-zone signals require verified play-by-play sources and are not claimed as tested.","Candidates require cross-season replication and approval before production changes."]}
def main():
 p=argparse.ArgumentParser();p.add_argument("--weekly-csv",type=Path,required=True);p.add_argument("--season",type=int,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 with a.weekly_csv.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
 out=evaluate(rows,a.season);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+"\n")
 print("Mix-and-match lab:",a.season,out["status"],out.get("candidate_improvements",[]),"production unchanged")
if __name__=="__main__":main()
