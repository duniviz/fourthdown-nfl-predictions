"""Grade only immutable official pregame game locks against completed NFL scores."""
import json
from datetime import datetime, timezone
from pathlib import Path
from live.game_pregame_observations import dt, number

ROOT=Path("data")
LOCKS=ROOT/"game-official-pregame-locks.json"
OUT=ROOT/"game-official-results.json"

def side(value):
    return "home" if value>0 else "away" if value<0 else "push"

def grade(locks,schedules):
    completed={str(g.get("game_id")):g for g in schedules
               if g.get("home_score") is not None and g.get("away_score") is not None}
    results=[]
    for row in locks:
        if not isinstance(row,dict) or row.get("lock_status")!="official":
            continue
        gid=str(row.get("game_id",""))
        game=completed.get(gid)
        if not game or not dt(row.get("kickoff_utc")):
            continue
        # Fail closed if the official record does not match the completed matchup.
        if game.get("home_team")!=row.get("home") or game.get("away_team")!=row.get("away"):
            continue
        home,away=number(game.get("home_score")),number(game.get("away_score"))
        projected_margin=number(row.get("projected_margin_home"))
        projected_total=number(row.get("projected_total"))
        if None in (home,away,projected_margin,projected_total):
            continue
        margin=home-away
        total=home+away
        winner=side(projected_margin)
        actual_winner=side(margin)
        winner_result="push" if actual_winner=="push" else (
            "not_available" if winner=="push" else "hit" if winner==actual_winner else "miss")
        spread=number(row.get("dk_home_spread"))
        model_ats=side(projected_margin+spread) if spread is not None else None
        actual_ats=side(margin+spread) if spread is not None else None
        ats_result=("not_available" if spread is None or model_ats=="push" else
                    "push" if actual_ats=="push" else "hit" if model_ats==actual_ats else "miss")
        line=number(row.get("dk_total"))
        model_ou=side(projected_total-line) if line is not None else None
        actual_ou=side(total-line) if line is not None else None
        ou_result=("not_available" if line is None or model_ou=="push" else
                   "push" if actual_ou=="push" else "hit" if model_ou==actual_ou else "miss")
        results.append({"game_id":gid,"season":row.get("season"),"week":row.get("week"),
            "home":row["home"],"away":row["away"],"kickoff_utc":row["kickoff_utc"],
            "lock_cutoff_utc":row.get("lock_cutoff_utc"),
            "forecast_at_utc":row.get("forecast_at_utc"),"dk_at_utc":row.get("dk_at_utc"),
            "home_score":home,"away_score":away,
            "projected_margin_home":projected_margin,"projected_total":projected_total,
            "dk_home_spread":spread,"dk_total":line,
            "winner_result":winner_result,"ats_result":ats_result,"ou_result":ou_result})
    return sorted(results,key=lambda x:(x["kickoff_utc"],x["game_id"]))

def summarize(rows):
    summary={}
    for key in ("winner","ats","ou"):
        values=[r[key+"_result"] for r in rows]
        hits=values.count("hit")
        misses=values.count("miss")
        summary[key]={"hits":hits,"misses":misses,"pushes":values.count("push"),
            "ungraded":values.count("not_available"),
            "hit_pct":round(100*hits/(hits+misses),1) if hits+misses else None}
    return summary

def main():
    import nflreadpy as nfl
    locks=json.loads(LOCKS.read_text()).get("records",[]) if LOCKS.exists() else []
    seasons=sorted({int(r["season"]) for r in locks if r.get("season") is not None})
    if not seasons:
        print("No official game locks to grade; leaving existing results unchanged")
        return
    schedules=[]
    for season in seasons:
        schedules.extend(nfl.load_schedules([season]).to_dicts())
    rows=grade(locks,schedules)
    data={"generated_at_utc":datetime.now(timezone.utc).isoformat(),
          "source":"immutable official 30-minute pregame game locks",
          "graded_games":len(rows),"summary":summarize(rows),"rows":rows}
    OUT.write_text(json.dumps(data,indent=2)+"\n")
    print(f"Graded {len(rows)} official game locks: {json.dumps(data['summary'])}")

if __name__=="__main__":
    main()
