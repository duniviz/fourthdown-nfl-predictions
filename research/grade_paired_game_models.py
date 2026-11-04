#!/usr/bin/env python3
"""Strict incumbent-versus-each-challenger paired game evaluation.

Never pool separate backtests or compare different game samples. Requires
both forecasts frozen before kickoff and the same verified final.
"""
import json,math,sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from same_slate_leaderboard import timestamp,finite

MARKETS=("game_margin_home","game_total")
def paired(rows,actuals):
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
    for key,models in groups.items():
        actual=finite(actuals.get(key))
        if actual is None:continue
        incumbent=models.get("live")
        if incumbent is None:
            rejected["missing_incumbent"]+=1;continue
        for model,challenger in models.items():
            if model=="live" or challenger is None:continue
            errors[(key[1],model)].append((key[0],abs(incumbent-actual),abs(challenger-actual)))
    results=[]
    for (market,model),pairs in sorted(errors.items()):
        n=len(pairs);base=sum(x[1] for x in pairs)/n;chall=sum(x[2] for x in pairs)/n
        weeks={g.split("_")[0]+"_"+g.split("_")[1] for g,_,_ in pairs}
        results.append({"market":market,"challenger":model,"matched_games":n,"independent_weeks":len(weeks),
                        "production_mae":round(base,4),"challenger_mae":round(chall,4),
                        "relative_improvement":round((base-chall)/base,5) if base else None,
                        "eligible_for_promotion":False,
                        "reason":"Pairwise comparison only; no verified QB-change labels, pregame PAR or deployable rollback"})
    return {"status":"PAIRED_SAME_GAME_EVALUATION","research_only":True,
            "production_modified":False,"auto_promotion_enabled":False,
            "comparisons":results,"rejected":dict(rejected)}
def main():
    from grade_yardage_game_models import get_game_actuals
    root=Path(__file__).resolve().parents[1]
    archive=json.loads((root/"data/weekly-shadow-forecasts.json").read_text()).get("rows",[])
    actuals=get_game_actuals(archive)
    report=paired(archive,actuals)
    dest=root/"research/paired-game-results";dest.mkdir(parents=True,exist_ok=True)
    (dest/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    lines=["# Exact production vs challenger: paired game grading","","Research only. No automatic deployment.","",
           "| Market | Challenger | Matched games | Weeks | Live MAE | Challenger MAE | Gain |",
           "|---|---|---:|---:|---:|---:|---:|"]
    for c in report["comparisons"]:
        gain="—" if c["relative_improvement"] is None else f'{100*c["relative_improvement"]:.2f}%'
        lines.append(f'| {c["market"]} | {c["challenger"]} | {c["matched_games"]} | {c["independent_weeks"]} | {c["production_mae"]} | {c["challenger_mae"]} | {gain} |')
    if not report["comparisons"]:lines.append("No completed games have paired frozen production and challenger forecasts yet.")
    (dest/"RESULTS.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))
if __name__=="__main__":main()
