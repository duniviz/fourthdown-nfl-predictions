"""Audit actual archived DraftKings player-line coverage; never synthesize missing odds."""
import argparse,json
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
MARKETS={"player_pass_yds","player_rec_yds","player_rush_yds"}
def dt(s):
    try:return datetime.fromisoformat(str(s).replace("Z","+00:00")).astimezone(timezone.utc)
    except (ValueError,TypeError):return None
def audit(snapshot):
    records=snapshot.get("records",[])
    totals=Counter();by_game=defaultdict(Counter);examples=[]
    for r in records:
        market=r.get("market")
        if market not in MARKETS:continue
        totals["yardage_records"]+=1
        game=str(r.get("game_id") or "unknown")
        kick=dt(r.get("kickoff"));captured=dt(r.get("dk_captured_at"))
        line=r.get("dk_line")
        if not isinstance(line,(int,float)) or isinstance(line,bool) or line<0:
            status="missing_line"
        elif not kick or not captured:
            status="missing_timestamp"
        elif captured>=kick:
            status="after_kickoff"
        else:status="usable_pregame"
        totals[status]+=1;by_game[game][status]+=1
        if status!="usable_pregame" and len(examples)<15:
            examples.append({"game_id":game,"player":r.get("player"),"market":market,"reason":status})
    return {"yardage_records":totals["yardage_records"],"usable_pregame":totals["usable_pregame"],
            "missing_line":totals["missing_line"],"missing_timestamp":totals["missing_timestamp"],
            "after_kickoff":totals["after_kickoff"],
            "games":{k:dict(v) for k,v in sorted(by_game.items())},
            "examples":examples}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshots",type=Path,default=Path("data/pregame-snapshots.json"))
    p.add_argument("--comparisons",type=Path,default=Path("data/research-dk-comparisons.json"))
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    snapshot=json.loads(a.snapshots.read_text())
    comparison=json.loads(a.comparisons.read_text())
    result={"research_only":True,"production_changed":False,
            "source":"repository archived DK pregame player snapshots",
            "snapshot_audit":audit(snapshot),
            "current_comparison_counts":comparison.get("counts",{}),
            "historical_backtest_ready":False,
            "approved_for_promotion":False,
            "next_requirement":"Accumulate verified pre-kickoff DK player yardage lines with matched player IDs and completed game actuals, then run chronological holdout on real over/under outcomes.",
            "limitations":["A missing or post-kickoff line cannot be used in a historical odds backtest",
                           "Current research comparison is not a multi-season historical archive",
                           "No betting performance or accuracy improvement is claimed"]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
