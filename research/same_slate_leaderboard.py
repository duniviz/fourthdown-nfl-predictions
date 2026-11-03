#!/usr/bin/env python3
"""Fail-closed same-slate leaderboard for archived, pregame model forecasts.

Input JSON: {"rows":[{"game_id":"2026_08_X_Y","player_id":"...","stat_key":"receiving_yards",
"model":"live","projection":65,"actual":70,"kickoff_utc":"...","predicted_at_utc":"...",
"dk_line":59.5}, ...]}. Multiple model rows must share the same game/player/market.
No postgame recomputation is permitted; missing pregame timestamps are excluded.
"""
import argparse, collections, datetime as dt, json, math, pathlib, statistics

def timestamp(value):
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z","+00:00")).astimezone(dt.timezone.utc)
    except (TypeError, ValueError): return None

def finite(value):
    try:
        n=float(value)
        return n if math.isfinite(n) else None
    except (TypeError,ValueError): return None

def compare(rows, week=None):
    groups=collections.defaultdict(dict)
    rejected=collections.Counter()\n    duplicate_keys=set()
    for row in rows:
        try:
            game=str(row["game_id"]); market=str(row["stat_key"]); player=str(row["player_id"])
            model=str(row["model"]); projection=finite(row["projection"]); actual=finite(row["actual"])
            kickoff=timestamp(row.get("kickoff_utc")); created=timestamp(row.get("predicted_at_utc"))
            if week is not None and int(game.split("_")[1])!=week: continue
            if not all((game,market,player,model)) or projection is None or actual is None or not kickoff or not created or created>=kickoff:
                rejected["invalid_or_not_pregame"]+=1;continue
            if row.get("dnp") or row.get("played") is False:
                rejected["dnp"]+=1;continue
            key=(game,player,market)
            if model in groups[key]:
                rejected["duplicate_model_forecast"]+=1
                del groups[key][model]
                continue
            groups[key][model]={"projection":projection,"actual":actual,"dk_line":finite(row.get("dk_line")),"predicted_at_utc":created.isoformat()}
        except (KeyError,ValueError,IndexError,TypeError):
            rejected["invalid_record"]+=1
    metrics=collections.defaultdict(list)
    matched=0
    for (game,player,market), forecasts in groups.items():
        if "live" not in forecasts or len(forecasts)<2:continue
        # All candidates must be evaluated on identical actuals and DK lines.
        actuals={round(v["actual"],6) for v in forecasts.values()}
        if len(actuals)!=1:
            rejected["conflicting_actuals"]+=1;continue
        matched+=1
        for model,v in forecasts.items():
            line=v["dk_line"]
            predicted_side=None if line is None or v["projection"]==line else v["projection"]>line
            actual_side=None if line is None or v["actual"]==line else v["actual"]>line
            hit=None if predicted_side is None or actual_side is None else int(predicted_side==actual_side)
            metrics[(market,model)].append((v["projection"]-v["actual"],hit))
    result=[]
    for (market,model), errors in sorted(metrics.items()):
        e=[x[0] for x in errors]; hits=[x[1] for x in errors if x[1] is not None]
        result.append({"market":market,"model":model,"n":len(e),"mae":round(statistics.mean(abs(x) for x in e),3),
                       "rmse":round(math.sqrt(statistics.mean(x*x for x in e)),3),
                       "dk_n":len(hits),"dk_hit_rate":round(statistics.mean(hits),4) if hits else None})
    # Do not rank models with different sample sizes as though coverage were identical.
    by_market=collections.defaultdict(list)
    for r in result:by_market[r["market"]].append(r)
    winners={}
    for market,rs in by_market.items():
        live=next((r for r in rs if r["model"]=="live"),None)
        if not live:continue
        eligible=[r for r in rs if r["model"]!="live" and r["n"]==live["n"] and r["n"]>=30]
        winners[market]=min(eligible,key=lambda r:(r["mae"],r["rmse"]))["model"] if eligible else None
    return {"research_only":True,"promotion_allowed":False,"matched_slate_records":matched,
            "rejected":dict(rejected),"metrics":result,"provisional_lowest_mae_challengers":winners,
            "warning":"Model coverage differs unless n matches; provisional winners are NOT promotion approvals."}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",default="research/same-slate/pregame-forecasts.json")
    ap.add_argument("--output",default="research/same-slate");ap.add_argument("--week",type=int)
    args=ap.parse_args();path=pathlib.Path(args.input)
    if not path.exists():raise SystemExit(f"No pregame multi-model forecast archive at {path}; no comparison generated")
    rows=json.loads(path.read_text());rows=rows["rows"] if isinstance(rows,dict) else rows
    report=compare(rows,args.week)
    if not report["matched_slate_records"]:raise SystemExit("No valid same-slate pregame model comparisons; refusing misleading leaderboard")
    dest=pathlib.Path(args.output);dest.mkdir(parents=True,exist_ok=True)
    (dest/"leaderboard.json").write_text(json.dumps(report,indent=2)+"\n")
    lines=["# Same-slate model leaderboard","","Research only; no automatic promotion.","",
           "| Market | Model | N | MAE | RMSE | DK bets | DK hit % |","|---|---|---:|---:|---:|---:|---:|"]
    for r in report["metrics"]:
        rate="—" if r["dk_hit_rate"] is None else f'{r["dk_hit_rate"]*100:.1f}%'
        lines.append(f'| {r["market"]} | {r["model"]} | {r["n"]} | {r["mae"]:.2f} | {r["rmse"]:.2f} | {r["dk_n"]} | {rate} |')
    lines+=["",f'Matched player/game/market records: {report["matched_slate_records"]}.',
            "Missing or post-kickoff forecasts are excluded. A candidate requires multiple independent weeks before promotion."]
    (dest/"LEADERBOARD.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))
if __name__=="__main__":main()
