#!/usr/bin/env python3
"""Normalize nflverse injury report to FOURTHDOWN pregame status CSV."""
import argparse
import csv
from pathlib import Path

STATUS={"out":"out","doubtful":"doubtful","questionable":"questionable",
        "ir":"inactive","injured reserve":"inactive","inactive":"inactive",
        "probable":"probable"}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--season",type=int,required=True)
    p.add_argument("--week",type=int,required=True)
    a=p.parse_args()
    latest={}
    with a.input.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        fields=set(reader.fieldnames or [])
        id_col=next((x for x in ("gsis_id","player_id") if x in fields),None)
        status_col=next((x for x in ("report_status","game_status","injury_status","status") if x in fields),None)
        date_col=next((x for x in ("date_modified","report_date","date","updated_at") if x in fields),None)
        if not {"season","week"}.issubset(fields) or not id_col or not status_col:
            p.error("Injury feed missing required columns; found: "+", ".join(sorted(fields)))
        for row in reader:
            try:
                if int(row["season"])!=a.season or int(row["week"])!=a.week:
                    continue
            except (ValueError,TypeError):
                continue
            if row.get("game_type",row.get("season_type","REG"))!="REG":
                continue
            pid=(row.get(id_col) or "").strip()
            if not pid:
                continue
            status=(row.get(status_col) or "").strip().lower()
            if status not in STATUS:
                continue  # No official designation is NOT proof of active status
            modified=(row.get(date_col) or "").strip() if date_col else "unknown"
            if pid not in latest or modified>latest[pid][0]:
                latest[pid]=(modified,STATUS[status])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=["season","week","player_id","status"])
        writer.writeheader()
        for pid,(_,status) in sorted(latest.items()):
            writer.writerow({"season":a.season,"week":a.week,"player_id":pid,"status":status})
    print(f"Normalized {len(latest)} explicit injury designations; undenoted players remain unverified")
if __name__=="__main__":
    main()
