#!/usr/bin/env python3
"""Leakage-safe, research-only QB passing yards model lab; production untouched."""
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path
from project_player_yards import project,opponent_defense

VARIANTS=("baseline","volume_efficiency","recent_volume","opponent_adjusted","game_script_proxy","combined")
def mean(a):return sum(a)/len(a)
def metrics(err):
 n=len(err)
 return {"samples":n,"mae":round(mean([abs(x) for x in err]),2),"rmse":round(math.sqrt(mean([x*x for x in err])),2),"bias":round(mean(err),2)} if n else {"samples":0,"mae":None,"rmse":None,"bias":None}
def validnum(v,lo=0,hi=1000):
 try:
  x=float(v)
  return x if math.isfinite(x) and lo<=x<=hi else None
 except (ValueError,TypeError):return None

def evaluate(rows,season,through_week,holdout_weeks=2,min_games=3):
 history=defaultdict(list)
 for r in rows:
  try:
   week=int(r["week"])
   if int(r["season"])!=season or not 1<=week<=through_week or r.get("season_type","REG")!="REG":continue
  except (ValueError,KeyError,TypeError):continue
  pid=r.get("player_id") or r.get("gsis_id")
  if not pid:continue
  yards=validnum(r.get("passing_yards"),0,700)
  attempts=validnum(r.get("attempts"),0,90)
  if yards is None or attempts is None:continue
  history[(week,pid)].append(r)
 start=max(min_games+1,through_week-holdout_weeks+1)
 errors={part:{variant:[] for variant in VARIANTS} for part in ("development","holdout")}
 coverage=defaultdict(int)
 for week in range(min_games+1,through_week+1):
  part="holdout" if week>=start else "development"
  baseline={p["player_id"]:p for p in project(rows,season,week,min_games=min_games) if p["market"]=="passing_yards"}
  defense=opponent_defense(rows,season,week,min_games=min_games)
  prior=defaultdict(list);team_points=defaultdict(list);opp_points=defaultdict(list)
  for r in rows:
   try:
    w=int(r["week"])
    if int(r["season"])!=season or not 1<=w<week or r.get("season_type","REG")!="REG":continue
   except (ValueError,TypeError,KeyError):continue
   pid=r.get("player_id") or r.get("gsis_id")
   y=validnum(r.get("passing_yards"),0,700);a=validnum(r.get("attempts"),0,90)
   if pid and y is not None and a is not None and a>0:prior[pid].append((w,a,y,r.get("opponent_team","")))
   team=r.get("recent_team") or r.get("team")
   pf=validnum(r.get("team_score"),0,100);pa=validnum(r.get("opponent_score"),0,100)
   if team and pf is not None and pa is not None:
    team_points[team].append((w,pf-pa))
  for pid,p in baseline.items():
   actual=history.get((week,pid),[])
   if len(actual)!=1:continue
   observed=validnum(actual[0].get("passing_yards"),0,700)
   if observed is None:continue
   games=sorted(prior[pid])
   if len(games)<min_games:continue
   last=games[-5:]
   attempts=mean([x[1] for x in last]);efficiency=sum(x[2] for x in last)/sum(x[1] for x in last)
   season_attempts=mean([x[1] for x in games]);season_eff=sum(x[2] for x in games)/sum(x[1] for x in games)
   volume=.65*attempts+.35*season_attempts
   ypa=.65*efficiency+.35*season_eff
   base=float(p["projected_yards"])
   opponent=actual[0].get("opponent_team","")
   factor=defense.get((opponent,"passing_yards"),1)
   # Score differential is a historical team trend, not a known pregame spread.
   team=p.get("team","")
   diffs=sorted(team_points.get(team,[]))
   trend=mean([x[1] for x in diffs[-5:]]) if diffs else 0
   script=max(.95,min(1.05,1-.002*trend))
   estimates={"baseline":base,"volume_efficiency":volume*ypa,
    "recent_volume":attempts*season_eff,"opponent_adjusted":base*factor,
    "game_script_proxy":base*script,"combined":volume*ypa*factor*script}
   for name,pred in estimates.items():
    if not math.isfinite(pred):raise ValueError("Invalid model estimate")
    errors[part][name].append(pred-observed)
   coverage[part]+=1
 results={part:{v:metrics(errors[part][v]) for v in VARIANTS} for part in errors}
 dev=results["development"];hold=results["holdout"];base=hold["baseline"]
 # No automatic promotion: improvement must be replicated on independent future data.
 candidates=[v for v in VARIANTS if v!="baseline" and dev[v]["samples"]>=30 and base["samples"]>=20
             and dev[v]["mae"]<dev["baseline"]["mae"] and dev[v]["rmse"]<dev["baseline"]["rmse"]
             and hold[v]["mae"]<base["mae"] and hold[v]["rmse"]<base["rmse"]]
 return {"status":"research_only_no_production_change","season":season,"through_week":through_week,
  "holdout_weeks":list(range(start,through_week+1)),"samples":dict(coverage),"results":results,
  "passing_yards_baseline_holdout":base,"candidate_improvements":candidates,
  "production_change_approved":False,"factors_tested":["recent_attempts","attempts_times_yards_per_attempt",
   "historical_opponent_pass_defense","historical_team_scoring_margin_game_script_proxy"],
  "limitations":["Historical team scoring margin is a game-script proxy, not a pregame spread.",
   "Opponent factor uses prior-week player data only when opponent_team is present.",
   "No weather observations are included; no pregame weather archive is available.",
   "Candidate results are exploratory and require independent future confirmation.",
   "Only QBs with both valid historical attempts and observed passing yards are graded."]}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--weekly-csv",type=Path,required=True)
 p.add_argument("--season",type=int,required=True)
 p.add_argument("--through-week",type=int,required=True)
 p.add_argument("--holdout-weeks",type=int,default=2)
 p.add_argument("--output",type=Path,required=True)
 a=p.parse_args()
 if a.holdout_weeks<1: p.error("holdout-weeks must be positive")
 with a.weekly_csv.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
 result=evaluate(rows,a.season,a.through_week,a.holdout_weeks)
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(result,indent=2)+"\n")
 print("Passing yards lab:",{"samples":result["samples"],"holdout":result["passing_yards_baseline_holdout"],"candidate_improvements":result["candidate_improvements"],"production_changed":False})
if __name__=="__main__":main()
