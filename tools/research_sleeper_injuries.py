#!/usr/bin/env python3
"""Supplemental Sleeper injury flags; never certify game-day availability."""
import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL="https://api.sleeper.app/v1/players/nfl"
FLAGS={"out":"out","doubtful":"doubtful","questionable":"questionable","ir":"injured_reserve","pup":"physically_unable_to_perform","susp":"suspended"}
def normalize(value):
    return FLAGS.get(str(value or "").strip().lower())
def build(players, projections):
    indexed={}
    for sleeper_id,player in players.items():
        if not isinstance(player,dict): continue
        gsis=str(player.get("gsis_id") or "").strip()
        if gsis: indexed.setdefault(gsis,[]).append((sleeper_id,player))
    results=[]
    for p in projections:
        pid=str(p.get("player_id") or "")
        matches=indexed.get(pid,[])
        flags={normalize(item.get("injury_status")) for _,item in matches}
        flags.discard(None)
        if len(matches)!=1 or len(flags)!=1: continue
        sid,player=matches[0]
        results.append({"player_id":pid,"player_name":p.get("player_name"),"team":p.get("team"),"market":p.get("market"),"sleeper_id":sid,"injury_flag":next(iter(flags)),"source":"Sleeper player profile","game_day_status_verified":False})
    return results
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--players-json",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    with args.players_json.open() as handle: projections=json.load(handle).get("projections",[])
    req=urllib.request.Request(URL,headers={"User-Agent":"FOURTHDOWN-injury-research/1.0"})
    with urllib.request.urlopen(req,timeout=45) as response:
        players=json.load(response)
    if not isinstance(players,dict): raise ValueError("Unexpected Sleeper API payload")
    flags=build(players,projections)
    result={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"source":"Sleeper public player profiles","status":"supplemental_research_only","week_specific":False,"game_day_status_verified":False,"note":"Sleeper injury_status lacks an independently verified game-specific update timestamp. Flags are informational only and MUST NOT certify active/inactive game-day eligibility.","projection_markets":len(projections),"flagged_markets":len(flags),"flags":flags}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print("Supplemental Sleeper injury flags:",len(flags),"of",len(projections),"markets; no eligibility changes")
if __name__=="__main__":main()
