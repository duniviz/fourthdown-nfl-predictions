#!/usr/bin/env python3
"""Audit official game-day inactive feed coverage; missing coverage never means active."""
import argparse,json
from pathlib import Path
from collections import Counter

def audit(payload,projections):
    games=payload.get("games",[])
    if not isinstance(games,list): raise ValueError("games must be a list")
    expected={str(p.get("game_id")) for p in projections if p.get("game_id")}
    confirmed=set();unavailable=set();reasons=[]
    for game in games:
        gid=str(game.get("game_id") or "")
        if not gid or gid not in expected:
            reasons.append("unknown_game_id");continue
        teams=game.get("teams",[])
        if len(teams)!=2 or any(t.get("status")!="confirmed" for t in teams):
            unavailable.add(gid);continue
        if not game.get("official_source_url") or not game.get("published_at"):
            unavailable.add(gid);continue
        confirmed.add(gid)
    uncovered=expected-confirmed
    return {"status":"coverage_audit_only","expected_games":len(expected),"confirmed_source_games":len(confirmed),"unverified_games":len(uncovered),"unverified_game_ids":sorted(uncovered),"reasons":dict(Counter(reasons)),"eligible_players":0,"note":"Feed coverage alone never verifies active player status; no recommendation eligibility changes."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--players-json",type=Path,required=True)
    p.add_argument("--inactives-json",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    players=json.loads(a.players_json.read_text()).get("projections",[])
    feed=json.loads(a.inactives_json.read_text())
    result=audit(feed,players)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print("Game-day coverage audit:",result["confirmed_source_games"],"confirmed-source games,",result["unverified_games"],"unverified; no player eligibility changes")
if __name__=="__main__":main()
