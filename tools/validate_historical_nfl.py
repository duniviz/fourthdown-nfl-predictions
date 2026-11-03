#!/usr/bin/env python3
"""Validate downloaded historical NFL data before training any challenger."""
import json
from pathlib import Path
import polars as pl

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/"data/training"
def validate(folder=FOLDER):
 manifest=json.loads((folder/"manifest.json").read_text())
 assert manifest["historical_outcomes_not_frozen_pregame_features"] is True
 report={"source":manifest["source"],"seasons":manifest["seasons"],"tables":{},
         "approved_for_live_promotion":False,"historical_data_not_pregame_snapshots":True}
 for name in ("schedules","player_stats","team_stats"):
  meta=manifest["datasets"][name]
  assert meta["status"]=="ready",f"{name}: not ready"
  path=folder/(name+".parquet")
  assert path.exists(),f"{name}: missing"
  df=pl.read_parquet(path)
  assert df.height>0 and df.height==meta["rows"],f"{name}: row mismatch"
  assert len(df.columns)>3,f"{name}: invalid schema"
  assert "season" in df.columns,f"{name}: missing season"
  seasons=set(df["season"].drop_nulls().cast(pl.Int64).to_list())
  assert seasons and seasons.issubset(set(manifest["seasons"])),f"{name}: unexpected season"
  report["tables"][name]={"rows":df.height,"columns":len(df.columns),
                          "seasons":sorted(seasons),"null_season_rows":df["season"].null_count()}
 assert len(report["tables"]["schedules"]["seasons"])>=2
 (folder/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps(report,indent=2))
 return report
if __name__=="__main__":validate()
