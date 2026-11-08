#!/usr/bin/env python3
"""Join actual frozen pregame snapshots to verified graded final player results.

No postgame forecast reconstruction. Only exact game/player/market matches.
"""
import argparse,collections,datetime as dt,json,pathlib
ALIASES={"player_pass_yds":"passing_yards","player_rush_yds":"rushing_yards","player_rec_yds":"receiving_yards","player_pass_completions":"completions","player_pass_attempts":"attempts","player_rush_attempts":"carries",
"player_receptions":"receptions","player_receiving_yards":"receiving_yards","player_rushing_yards":"rushing_yards",
"player_passing_yards":"passing_yards","passing_yards":"passing_yards","receiving_yards":"receiving_yards",
"rushing_yards":"rushing_yards","receptions":"receptions","completions":"completions","attempts":"attempts","carries":"carries"}
def norm(v):return ALIASES.get(str(v),str(v))
def parse(s):
 try:return dt.datetime.fromisoformat(str(s).replace("Z","+00:00")).astimezone(dt.timezone.utc)
 except (ValueError,TypeError):return None
def join(snapshots,results):
 actuals={}; ambiguous=set()
 for r in results:
  try:
   key=(str(r["game_id"]),str(r["player_id"]),norm(r["stat_key"]))
   if r.get("dnp") or r.get("played") is False or r.get("actual") is None:continue
   val=float(r["actual"])
   if key in actuals and actuals[key]!=val:ambiguous.add(key)
   actuals[key]=val
  except (KeyError,ValueError,TypeError):continue
 rows=[]; rejected=collections.Counter()
 for s in snapshots:
  try:
   key=(str(s["game_id"]),str(s["player_id"]),norm(s["market"]))
   captured=parse(s.get("captured_at"));kickoff=parse(s.get("kickoff"))
   if not captured or not kickoff or captured>=kickoff:
    rejected["missing_or_invalid_pregame_time"]+=1;continue
   if key in ambiguous or key not in actuals:
    rejected["no_verified_matching_final"]+=1;continue
   line=s.get("dk_line");qtime=parse(s.get("dk_captured_at"))
   if line is not None and (not qtime or qtime>=kickoff):
    line=None
   rows.append({"game_id":key[0],"player_id":key[1],"stat_key":key[2],
    "player":s.get("player"),"team":s.get("team"),"projection":float(s["projection"]),
    "actual":actuals[key],"dk_line":line,"kickoff_utc":kickoff.isoformat(),
    "predicted_at_utc":captured.isoformat()})
  except (KeyError,TypeError,ValueError):rejected["invalid_snapshot"]+=1
 return {"rows":rows,"rejected":dict(rejected),"source":"frozen_pregame_snapshots_joined_to_verified_final_results"}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--snapshots",default="data/pregame-snapshots.json");ap.add_argument("--results",default="data/player-results.json");ap.add_argument("--output",default="research/same-slate/verified-input.json");args=ap.parse_args()
 s=json.loads(pathlib.Path(args.snapshots).read_text()).get("records",[])
 r=json.loads(pathlib.Path(args.results).read_text()).get("rows",[])
 payload=join(s,r)
 if not payload["rows"]:raise SystemExit("No graded frozen pregame snapshots match verified finals yet")
 p=pathlib.Path(args.output);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(payload,indent=2)+"\n")
 print(f'Joined {len(payload["rows"])} verified pregame rows; rejected {payload["rejected"]}')
if __name__=="__main__":main()
