#!/usr/bin/env python3
"""Strict incumbent-versus-each-challenger paired game evaluation.

Never pool separate backtests or compare different game samples. Requires
both forecasts frozen before kickoff and the same verified final.
"""
import json,math,sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from same_slate_leaderboard import timestamp,finite

MARKETS=("game_margin_home","game_total")
def paired(rows,actuals,official_lines=None):
    official_lines=official_lines or {}
    groups=defaultdict(dict)
    rejected=defaultdict(int)
    for r in rows:
        if r.get("player_id")!="GAME" or r.get("stat_key") not in MARKETS:continue
        key=(str(r.get("game_id")),r["stat_key"])
        kick=timestamp(r.get("kickoff_utc"));pred=timestamp(r.get("predicted_at_utc"))
        value=finite(r.get("projection"))
        if not kick or not pred or pred>=kick or value is None:
            rejected["invalid_pregame_forecast"]+=1;continue
        model=r.get("model")
        if model in groups[key]:
            groups[key][model]=None
            rejected["duplicate_forecast"]+=1
        else:groups[key][model]=value
    errors=defaultdict(list)
    picks=defaultdict(lambda:{"hits":0,"misses":0,"pushes":0,"no_pick":0})
    for key,models in groups.items():
        actual=finite(actuals.get(key))
        if actual is None:continue
        incumbent=models.get("live")
        if incumbent is None:
            rejected["missing_incumbent"]+=1;continue
        for model,challenger in models.items():
            if model=="live" or challenger is None:continue
            errors[(key[1],model)].append((key[0],abs(incumbent-actual),abs(challenger-actual)))
        # Score pick outcomes for each model on the same frozen game and verified
        # closing snapshot. Winner grading needs no sportsbook quote; ATS/O-U do.
        gid,market=key
        if market=="game_margin_home":
            actual_margin=actual
            line=official_lines.get(gid,{})
            home_spread=finite(line.get("dk_home_spread"))
            winner_actual=1 if actual_margin>0 else -1 if actual_margin<0 else 0
            for model,prediction in models.items():
                if prediction is None:continue
                predicted=1 if prediction>0 else -1 if prediction<0 else 0
                if winner_actual==0:
                    picks[("winner",model)]["pushes"]+=1
                elif predicted==0:
                    picks[("winner",model)]["no_pick"]+=1
                else:
                    picks[("winner",model)]["hits" if predicted==winner_actual else "misses"]+=1
                if home_spread is not None:
                    actual_side=1 if actual_margin+home_spread>0 else -1 if actual_margin+home_spread<0 else 0
                    predicted_side=1 if prediction+home_spread>0 else -1 if prediction+home_spread<0 else 0
                    grade_pick(picks[("ats",model)],predicted_side,actual_side)
        elif market=="game_total":
            line=official_lines.get(gid,{})
            total_line=finite(line.get("dk_total"))
            if total_line is not None:
                actual_side=1 if actual>total_line else -1 if actual<total_line else 0
                for model,prediction in models.items():
                    if prediction is None:continue
                    predicted_side=1 if prediction>total_line else -1 if prediction<total_line else 0
                    grade_pick(picks[("over_under",model)],predicted_side,actual_side)
    results=[]
    for (market,model),pairs in sorted(errors.items()):
        n=len(pairs);base=sum(x[1] for x in pairs)/n;chall=sum(x[2] for x in pairs)/n
        weeks={g.split("_")[0]+"_"+g.split("_")[1] for g,_,_ in pairs}
        results.append({"market":market,"challenger":model,"matched_games":n,"independent_weeks":len(weeks),
                        "production_mae":round(base,4),"challenger_mae":round(chall,4),
                        "relative_improvement":round((base-chall)/base,5) if base else None,
                        "eligible_for_promotion":False,
                        "reason":"Pairwise comparison only; no verified QB-change labels, pregame PAR or deployable rollback"})
    pick_results=[]
    for (market,model),counts in sorted(picks.items()):
        decisions=counts["hits"]+counts["misses"]
        pick_results.append({"market":market,"model":model,**counts,
            "graded_picks":decisions,
            "hit_pct":round(100*counts["hits"]/decisions,2) if decisions else None})
    return {"status":"PAIRED_SAME_GAME_EVALUATION","research_only":True,
            "production_modified":False,"auto_promotion_enabled":False,
            "comparisons":results,"pick_results":pick_results,
            "rejected":dict(rejected)}

def grade_pick(counts,predicted_side,actual_side):
    if actual_side==0:
        counts["pushes"]+=1
    elif predicted_side==0:
        counts["no_pick"]+=1
    else:
        counts["hits" if predicted_side==actual_side else "misses"]+=1
def main():
    from grade_yardage_game_models import get_game_actuals
    root=Path(__file__).resolve().parents[1]
    archive=json.loads((root/"data/weekly-shadow-forecasts.json").read_text()).get("rows",[])
    actuals=get_game_actuals(archive)
    actuals={(game,market):score for (game,player,market),score in actuals.items() if player=="GAME"}
    official=json.loads((root/"data/game-official-pregame-locks.json").read_text()).get("records",[]) if (root/"data/game-official-pregame-locks.json").exists() else []
    lines={}
    for lock in official:
        if lock.get("lock_status")!="official":continue
        kick=timestamp(lock.get("kickoff_utc"));quoted=timestamp(lock.get("dk_at_utc"))
        captured=timestamp(lock.get("captured_at_utc"));cutoff=timestamp(lock.get("lock_cutoff_utc"))
        if (not kick or not quoted or not captured or not cutoff
                or cutoff!=kick-timedelta(minutes=15)
                or not cutoff-timedelta(minutes=90)<=quoted<=cutoff
                or captured>cutoff):continue
        lines[str(lock.get("game_id"))]={"dk_home_spread":lock.get("dk_home_spread"),"dk_total":lock.get("dk_total")}
    report=paired(archive,actuals,lines)
    dest=root/"research/paired-game-results";dest.mkdir(parents=True,exist_ok=True)
    (dest/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    lines=["# Exact production vs challenger: paired game grading","","Research only. No automatic deployment.","",
           "| Market | Challenger | Matched games | Weeks | Live MAE | Challenger MAE | Gain |",
           "|---|---|---:|---:|---:|---:|---:|"]
    for c in report["comparisons"]:
        gain="—" if c["relative_improvement"] is None else f'{100*c["relative_improvement"]:.2f}%'
        lines.append(f'| {c["market"]} | {c["challenger"]} | {c["matched_games"]} | {c["independent_weeks"]} | {c["production_mae"]} | {c["challenger_mae"]} | {gain} |')
    if not report["comparisons"]:lines.append("No completed games have paired frozen production and challenger forecasts yet.")
    lines += ["", "## Pick grading on paired games", "", "| Pick | Model | Graded | Hits | Misses | Pushes | No pick | Hit % |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for item in report["pick_results"]:
        pct="—" if item["hit_pct"] is None else f'{item["hit_pct"]:.2f}%'
        lines.append(f'| {item["market"]} | {item["model"]} | {item["graded_picks"]} | {item["hits"]} | {item["misses"]} | {item["pushes"]} | {item["no_pick"]} | {pct} |')
    if not report["pick_results"]:lines.append("No paired completed game pick outcomes are available.")
    lines += ["", "ATS and over/under grades require an official, timestamped pregame DraftKings line. Winner grades do not require odds. Pushes and model no-picks are excluded from hit-rate denominators."]
    (dest/"RESULTS.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))
if __name__=="__main__":main()
