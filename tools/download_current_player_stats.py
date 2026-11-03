#!/usr/bin/env python3
"""Fetch season-specific weekly nflverse player stats from the current release.

Discover actual asset names from GitHub API, rather than downloading the
legacy all-years CSV (which currently ends in 2024).
"""
import argparse
import csv
import json
import os
import sys
import urllib.request
from pathlib import Path

API="https://api.github.com/repos/nflverse/nflverse-data/releases/tags/stats_player"
def fetch(url):
    headers={"User-Agent":"FOURTHDOWN-research/1.0","Accept":"application/vnd.github+json"}
    token=os.environ.get("GITHUB_TOKEN","").strip()
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"]="Bearer "+token
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=90) as response:
        return response.read()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--season",type=int,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    release=json.loads(fetch(API))
    assets=release.get("assets",[])
    candidates=[]
    for item in assets:
        name=item.get("name","").lower()
        if str(a.season) not in name or not name.endswith((".csv",".parquet")):
            continue
        if not ("week" in name and ("player" in name or "stats" in name)):
            continue
        candidates.append(item)
    candidates.sort(key=lambda x:(not x["name"].lower().endswith(".csv"),len(x["name"])))
    if not candidates:
        nearby=[x.get("name") for x in assets if str(a.season) in x.get("name","")][:30]
        raise SystemExit(f"No season-specific weekly player stats asset for {a.season}; available matching assets: {nearby}")
    asset=candidates[0]
    print(f"Selected nflverse asset: {asset['name']}",flush=True)
    blob=fetch(asset["browser_download_url"])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if asset["name"].lower().endswith(".csv"):
        a.output.write_bytes(blob)
    else:
        try:
            import polars as pl
        except ImportError as exc:
            raise SystemExit("Parquet player stats require polars") from exc
        import io
        pl.read_parquet(io.BytesIO(blob)).write_csv(a.output)
    with a.output.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        cols=set(reader.fieldnames or [])
        required={"season","week","player_id","passing_yards","rushing_yards","receiving_yards"}
        if not required.issubset(cols):
            raise SystemExit(f"Unsupported player stats schema: missing {sorted(required-cols)}")
        n=sum(1 for row in reader if row.get("season")==str(a.season))
    if n<100:
        raise SystemExit(f"Insufficient {a.season} player records: {n}")
    print(f"Validated {n} rows for season {a.season}")
if __name__=="__main__":
    main()
