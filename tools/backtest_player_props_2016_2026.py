#!/usr/bin/env python3
"""Research-only chronological player-prop comparisons for 2016–2026."""
import argparse,json,math,sys
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import nflreadpy as nfl
from live.backtest_players import backtest
from tools.backtest_count_props_walkforward import evaluate as evaluate_counts

def report(rows):
    out={}
    for season in sorted({r["season"] for r in rows}):
        out[str(season)]={}
        for market in sorted({r["market"] for r in rows}):
            subset=[r for r in rows if r["season"]==season and r["market"]==market]
            if not subset:continue
            out[str(season)][market]={"samples":len(subset),"baseline_mae":round(sum(r["old_abs_error"] for r in subset)/len(subset),3),"candidate_mae":round(sum(r["new_abs_error"] for r in subset)/len(subset),3)}
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",type=int,default=2016)
    p.add_argument("--end",type=int,default=2026)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if not 2016<=a.start<=a.end<=2026:p.error("Use seasons within 2016–2026")
    seasons=list(range(a.start,a.end+1))
    yards=backtest(tuple(seasons))
    if not yards:raise RuntimeError("No eligible yardage samples")
    counts=[]
    for season in seasons:
        raw=nfl.load_player_stats([season],summary_level="week").to_dicts()
        counts.extend(raw)
    count_report=evaluate_counts(counts,set(seasons))
    result={"status":"research_only","seasons":seasons,"yards_by_season":report(yards),
            "yards_all":{market:{"samples":len(group),"baseline_mae":round(sum(r["old_abs_error"] for r in group)/len(group),3),"candidate_mae":round(sum(r["new_abs_error"] for r in group)/len(group),3)} for market in sorted({r["market"] for r in yards}) for group in [[r for r in yards if r["market"]==market]]},
            "counts":count_report,"production_changed":False,
            "limitations":["Historical observed-player cohort; not identical to archived live-production predictions.","Each forecast uses earlier weeks of its season; no same-week outcomes.","2026 partial; no DK odds, returns, or promotion evidence."]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"yards_all":result["yards_all"],"counts":count_report["markets"],"seasons":seasons},indent=2))

if __name__=="__main__":main()
