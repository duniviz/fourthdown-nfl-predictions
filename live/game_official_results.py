"""Grade valid pregame game forecasts against verified completed scores."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from live.game_pregame_observations import dt, number

CENTRAL=ZoneInfo("America/Chicago")
GRADEABLE=("official","forecast_only","last_available","early_pregame")

ROOT=Path("data")
LOCKS=ROOT/"game-official-pregame-locks.json"
OUT=ROOT/"game-official-results.json"

def side(value):
    return "home" if value>0 else "away" if value<0 else "push"

def nightly_grade_due(now, last_graded_at, event_name, pending_kickoffs=()):
    """Grade at 11 PM Central, and also when that cron starts hours late.

    GitHub often delivers the 11 PM Central schedule the next morning. A
    morning run still grades when nothing has been published since 11 PM, so
    a Sunday-night final is not left until the following night.
    """
    if event_name=="pull_request":
        return False
    if event_name!="schedule":
        return True
    local=now.astimezone(CENTRAL)
    if local.hour==23:
        return True
    last_eleven=local.replace(hour=23, minute=0, second=0, microsecond=0)
    if local<last_eleven:
        last_eleven-=timedelta(days=1)
    graded=last_graded_at.astimezone(CENTRAL) if last_graded_at else None
    if graded is None or graded<last_eleven:
        return True
    for kickoff in pending_kickoffs:
        if kickoff<=now-timedelta(hours=3) and graded<kickoff:
            return True
    return False

def ungraded_kickoffs(locks, graded_rows):
    graded={str(r.get("game_id")) for r in graded_rows if isinstance(r,dict)}
    kickoffs=[]
    for row in locks:
        if not isinstance(row,dict) or str(row.get("game_id")) in graded:
            continue
        if row.get("lock_status") not in GRADEABLE:
            continue
        kickoff=dt(row.get("kickoff_utc"))
        if kickoff:
            kickoffs.append(kickoff)
    return kickoffs

def grade(locks,schedules):
    completed={str(g.get("game_id")):g for g in schedules
               if g.get("home_score") is not None and g.get("away_score") is not None}
    results=[]
    for row in locks:
        if not isinstance(row,dict) or row.get("lock_status") not in GRADEABLE:
            continue
        gid=str(row.get("game_id",""))
        game=completed.get(gid)
        if not game or not dt(row.get("kickoff_utc")):
            continue
        kickoff=dt(row.get("kickoff_utc"))
        predicted=dt(row.get("forecast_at_utc"))
        captured=dt(row.get("captured_at_utc"))
        if not predicted or not captured or not predicted<=captured<kickoff:
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
        quote=dt(row.get("dk_at_utc"))
        quote_valid=bool(quote and quote<=captured and quote<kickoff and row.get("lock_status")!="forecast_only")
        spread=number(row.get("dk_home_spread")) if quote_valid else None
        model_ats=side(projected_margin+spread) if spread is not None else None
        actual_ats=side(margin+spread) if spread is not None else None
        ats_result=("not_available" if spread is None or model_ats=="push" else
                    "push" if actual_ats=="push" else "hit" if model_ats==actual_ats else "miss")
        line=number(row.get("dk_total")) if quote_valid else None
        model_ou=side(projected_total-line) if line is not None else None
        actual_ou=side(total-line) if line is not None else None
        ou_result=("not_available" if line is None or model_ou=="push" else
                   "push" if actual_ou=="push" else "hit" if model_ou==actual_ou else "miss")
        results.append({"game_id":gid,"season":row.get("season"),"week":row.get("week"),
            "home":row["home"],"away":row["away"],"kickoff_utc":row["kickoff_utc"],"lock_status":row["lock_status"],
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
    import sys
    if "--due" in sys.argv:
        event="schedule"
        if "--event" in sys.argv:
            event=sys.argv[sys.argv.index("--event")+1]
        now=datetime.now(timezone.utc)
        locks=json.loads(LOCKS.read_text()).get("records",[]) if LOCKS.exists() else []
        saved=json.loads(OUT.read_text()) if OUT.exists() else {}
        due=nightly_grade_due(now, dt(saved.get("generated_at_utc")), event,
                              ungraded_kickoffs(locks, saved.get("rows") or []))
        print("Nightly grading due" if due else "Nightly grading not due")
        raise SystemExit(0 if due else 1)
    import nflreadpy as nfl
    locks=json.loads(LOCKS.read_text()).get("records",[]) if LOCKS.exists() else []
    seasons=sorted({int(r["season"]) for r in locks if r.get("season") is not None})
    schedules=[]
    for season in seasons:
        schedules.extend(nfl.load_schedules([season]).to_dicts())
    rows=grade(locks,schedules)
    data={"generated_at_utc":datetime.now(timezone.utc).isoformat(),
          "source":"timestamped pregame game forecast locks",
          "graded_games":len(rows),"summary":summarize(rows),"rows":rows}
    OUT.write_text(json.dumps(data,indent=2)+"\n")
    print(f"Graded {len(rows)} official game locks: {json.dumps(data['summary'])}")

if __name__=="__main__":
    main()
