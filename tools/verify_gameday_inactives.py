#!/usr/bin/env python3
"""Validate externally sourced, game-specific NFL inactive reports; fail closed."""
import argparse,csv,json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import urlparse

def verify(rows,projections,now):
    ids={str(p.get("player_id")) for p in projections}
    output=[]; rejected=[]
    seen=set()
    for row in rows:
        pid=str(row.get("player_id") or "").strip()
        url=str(row.get("source_url") or "").strip()
        try:
            published=datetime.fromisoformat(str(row.get("published_at_utc") or "").replace("Z","+00:00"))
            kickoff=datetime.fromisoformat(str(row.get("kickoff_at_utc") or "").replace("Z","+00:00"))
            if published.utcoffset()!=timedelta(0) or kickoff.utcoffset()!=timedelta(0): raise ValueError("UTC required")
            if not (kickoff-timedelta(hours=4)<=published<=min(now,kickoff+timedelta(hours=1))): raise ValueError("outside pregame window")
            if not (kickoff-timedelta(hours=4)<=now<=kickoff+timedelta(hours=1)): raise ValueError("not current game window")
            parsed=urlparse(url)
            if parsed.scheme!="https" or not parsed.netloc or parsed.username: raise ValueError("source URL invalid")
            if str(row.get("status") or "").strip().lower()!="inactive": raise ValueError("only explicit inactive supported")
            if pid not in ids: raise ValueError("unknown projected player ID")
            if pid in seen: raise ValueError("duplicate player")
            seen.add(pid)
            output.append({"player_id":pid,"status":"inactive","source_url":url,"published_at_utc":published.isoformat(),"kickoff_at_utc":kickoff.isoformat(),"verified_source":False})
        except (ValueError,TypeError) as e:
            rejected.append({"player_id":pid,"reason":str(e)})
    return output,rejected

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--players-json",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    players=json.loads(a.players_json.read_text()).get("projections",[])
    rows=list(csv.DictReader(a.input.open(newline="",encoding="utf-8-sig")))
    valid,rejected=verify(rows,players,datetime.now(timezone.utc))
    payload={"status":"source_claims_pending_independent_verification","note":"Source URLs and report timestamps are supplied assertions, NOT independently verified official NFL inactive reports. Never use this file to certify player eligibility.","inactive_claims":valid,"rejected":rejected,"generated_at_utc":datetime.now(timezone.utc).isoformat()}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(payload,indent=2)+"\n")
    print("Inactive source claims:",len(valid),"rejected:",len(rejected),"; no automatic eligibility changes")
if __name__=="__main__":main()
