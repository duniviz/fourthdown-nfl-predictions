#!/usr/bin/env python3
"""Audit published pregame prop results without inventing missing observations."""
import json
import math
from pathlib import Path

def audit(rows):
    problems=[]
    seen=set()
    for i,r in enumerate(rows):
        ident=(str(r.get("game_id")),str(r.get("player_id")),str(r.get("stat_key")))
        if ident in seen: problems.append(f"row {i}: duplicate graded player/market/game")
        seen.add(ident)
        line=r.get("dk_line")
        side=str(r.get("recommended_side") or "").lower()
        grade=r.get("recommendation_result")
        if line is None:
            if grade not in ("not_available",None):
                problems.append(f"row {i}: graded without archived DK line")
            continue
        if not isinstance(line,(int,float)) or not math.isfinite(line) or line<=0:
            problems.append(f"row {i}: invalid DK line")
            continue
        if side not in ("over","under"):
            if grade not in ("not_available",None):
                problems.append(f"row {i}: graded without saved side")
            continue
        actual=r.get("actual")
        if not isinstance(actual,(int,float)) or not math.isfinite(actual):
            problems.append(f"row {i}: invalid actual for graded recommendation")
            continue
        expected="push" if actual==line else ("hit" if (actual>line)==(side=="over") else "miss")
        if grade!=expected: problems.append(f"row {i}: expected {expected}, found {grade}")
    return problems

def main():
    p=Path("data/player-results.json")
    payload=json.loads(p.read_text())
    rows=payload.get("rows")
    if not isinstance(rows,list): raise SystemExit("Invalid player results rows")
    errors=audit(rows)
    with_lines=sum(r.get("dk_line") is not None for r in rows)
    with_saved_sides=sum(str(r.get("recommended_side") or "").lower() in ("over","under") for r in rows)
    graded=sum(r.get("recommendation_result") in ("hit","miss","push") for r in rows)
    print(f"Checked {len(rows)} player results; DK lines: {with_lines}; saved sides: {with_saved_sides}; graded picks: {graded}; issues: {len(errors)}")
    if not graded:
        print("NOTICE: No eligible archived pregame recommendations. Do not publish a hit rate.")
    for e in errors[:25]:print("ERROR:",e)
    if errors:raise SystemExit(1)

if __name__=="__main__":main()
