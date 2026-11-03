"""Research-only weather challengers for frozen game scores and player props.

Requires one pregame forecast per row, timestamped before kickoff, with a
historical baseline projection and verified final result. No live adjustments.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path
from tools.weather_combo_research import COMBOS,feature,number,timestamp

FIELDS={"season","week","game_id","player_id","market","kickoff_utc","forecast_captured_at_utc",
        "forecast_wind_mph","forecast_temp_f","forecast_precip_pct","roof_status",
        "baseline_projection","actual"}
MARKETS={"game_total","home_score","away_score","passing_yards","rushing_yards",
         "receiving_yards","pass_attempts","rush_attempts","receptions","field_goals_made"}
def evaluate(path):
    with Path(path).open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        if not FIELDS.issubset(reader.fieldnames or []):
            raise ValueError("Missing required frozen game/player forecast columns")
        rows=list(reader)
    seen=set();valid=[];rejected=defaultdict(int)
    for r in rows:
        try:
            season=int(r["season"]);week=int(r["week"])
            game=r["game_id"].strip();player=r["player_id"].strip();market=r["market"].strip()
            if season<1 or week<1 or not game or market not in MARKETS:raise ValueError()
            if market not in ("game_total","home_score","away_score") and not player:raise ValueError()
            key=(season,week,game,player,market)
        except (ValueError,TypeError,AttributeError):
            rejected["invalid_key_or_market"]+=1;continue
        if key in seen:raise ValueError("Duplicate frozen forecast key: "+repr(key))
        seen.add(key)
        kickoff=timestamp(r["kickoff_utc"]);captured=timestamp(r["forecast_captured_at_utc"])
        if not kickoff or not captured or captured>=kickoff:
            rejected["unverified_pregame"]+=1;continue
        f=feature(r);baseline=number(r["baseline_projection"]);actual=number(r["actual"])
        if f is None or baseline is None or actual is None or baseline<0 or actual<0:
            rejected["invalid_weather_or_result"]+=1;continue
        valid.append((season,week,market,f,baseline,actual))
    seasons=sorted({r[0] for r in valid})
    report={}
    if len(seasons)>=2:
        holdout=seasons[-1]
        for market in sorted({r[2] for r in valid}):
            tr=[r for r in valid if r[0]<holdout and r[2]==market]
            ho=[r for r in valid if r[0]==holdout and r[2]==market]
            combinations={}
            for name,rule in COMBOS.items():
                train=[r for r in tr if rule(r[3])]
                test=[r for r in ho if rule(r[3])]
                if len(train)<30 or len(test)<20:
                    combinations[name]={"status":"insufficient_samples","train_n":len(train),"holdout_n":len(test)}
                    continue
                offset=sum(r[5]-r[4] for r in train)/len(train)
                # Conservative exploratory cap: 10% of historical baseline magnitude.
                cap=max(0.5,sum(r[4] for r in train)/len(train)*0.1)
                offset=max(-cap,min(cap,offset))*len(train)/(len(train)+100)
                old=sum(abs(r[5]-r[4]) for r in test)/len(test)
                new=sum(abs(r[5]-max(0,r[4]+offset)) for r in test)/len(test)
                combinations[name]={"status":"holdout_evaluated","train_n":len(train),"holdout_n":len(test),
                    "frozen_offset":round(offset,3),"baseline_mae":round(old,3),
                    "challenger_mae":round(new,3),"mae_improvement":round(old-new,3)}
            report[market]=combinations
    return {"research_only":True,"production_changed":False,"eligible_for_promotion":False,
        "status":"holdout_evaluated" if len(seasons)>=2 else "insufficient_chronological_seasons",
        "holdout_season":seasons[-1] if len(seasons)>=2 else None,
        "valid_rows":len(valid),"rejected":dict(rejected),"markets":report,
        "warning":"Exploratory correlated weather scenarios. Must verify historical pregame forecast provenance, same-slate comparisons, independent holdouts and player opportunity impacts before production."}
def main():
    path=Path("data/backtests/weather-frozen-markets.csv")
    if not path.exists():
        print("No timestamped frozen game/player market history; skipping, no fabricated results")
        return
    report=evaluate(path)
    Path("data/weather-market-research.json").write_text(json.dumps(report,indent=2)+"\n")
    print(report["status"],report["valid_rows"])
if __name__=="__main__":main()
