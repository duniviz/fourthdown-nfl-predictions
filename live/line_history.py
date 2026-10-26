"""Archive timestamped DraftKings lines without overwriting earlier snapshots."""
import json
from pathlib import Path
from datetime import datetime,timezone
def main():
    p=Path("data/dk-odds.json")
    if not p.exists():return
    d=json.loads(p.read_text())
    target=Path("data/dk-line-history.json")
    try: old=json.loads(target.read_text()).get("rows",[])
    except (OSError,ValueError):old=[]
    seen={(x.get("player"),x.get("market_key"),x.get("commence_time"),x.get("last_update"),x.get("line")) for x in old}
    for r in d.get("rows",[]):
        if not r.get("last_update") or r.get("line") is None:continue
        key=(r.get("player"),r.get("market_key"),r.get("commence_time"),r.get("last_update"),r.get("line"))
        if key not in seen:
            old.append({k:r.get(k) for k in ("player","market_key","commence_time","last_update","line","over_price","under_price")})
            seen.add(key)
    old=old[-25000:]
    target.write_text(json.dumps({"updated_at_utc":datetime.now(timezone.utc).isoformat(),"rows":old},indent=2)+"\n")
    print("Saved",len(old),"timestamped line observations")
if __name__=="__main__":main()
