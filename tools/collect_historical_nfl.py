#!/usr/bin/env python3
"""Fetch historical NFL training inputs from nflverse; never modify live predictions.

Store only compact game/player tables, preserve source provenance, and do not
misrepresent retrospective data as frozen historical pregame predictions.
"""
import argparse,json,datetime as dt
from pathlib import Path
import nflreadpy as nfl

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"data/training"
TABLES={
 "schedules":lambda years:nfl.load_schedules(years),
 "player_stats":lambda years:nfl.load_player_stats(years),
 "team_stats":lambda years:nfl.load_team_stats(years),
}
def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--start",type=int,default=2022)
 parser.add_argument("--end",type=int,default=dt.datetime.now(dt.timezone.utc).year)
 args=parser.parse_args()
 if args.start<1999 or args.end<args.start or args.end>dt.datetime.now(dt.timezone.utc).year:
  parser.error("Invalid season range")
 years=list(range(args.start,args.end+1))
 DEST.mkdir(parents=True,exist_ok=True)
 manifest={"generated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
           "source":"nflverse via nflreadpy","seasons":years,
           "historical_outcomes_not_frozen_pregame_features":True,"datasets":{}}
 for name,loader in TABLES.items():
  try:
   df=loader(years)
   if df.is_empty():raise ValueError("empty source")
   output=DEST/(name+".parquet")
   df.write_parquet(output,compression="zstd")
   manifest["datasets"][name]={"rows":df.height,"columns":df.columns,
                               "path":str(output.relative_to(ROOT)),"status":"ready"}
   print(f"{name}: {df.height} rows")
  except Exception as exc:
   manifest["datasets"][name]={"status":"failed","error":str(exc)[:300]}
   print(f"{name}: FAILED {exc}")
 (DEST/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
 if any(x["status"]!="ready" for x in manifest["datasets"].values()):
  raise SystemExit("Incomplete historical collection; inspect manifest")
if __name__=="__main__":main()
