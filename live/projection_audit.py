"""Conservative, explainable outlier audit; never change model predictions."""
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

YARD_MARKETS={"passing_yards","rushing_yards","receiving_yards"}
def audit(players):
    if not isinstance(players,list):
        raise ValueError("Missing player records")
    flags=[]
    seen=set()
    by_game=defaultdict(list)
    for p in players:
        identity=(str(p.get("game_id")),str(p.get("player_id")),str(p.get("stat_key")))
        if identity in seen:
            flags.append(dict(severity="error",code="duplicate_market",player=p.get("player"),stat_key=p.get("stat_key"),game_id=p.get("game_id"),reason="Duplicate player/game/market"))
        seen.add(identity)
        by_game[(p.get("game_id"),p.get("team"))].append(p)
        stat=p.get("stat_key")
        name=p.get("player")
        value=p.get("projection")
        if not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
            flags.append(dict(severity="error",code="invalid_projection",player=name,stat_key=stat,game_id=p.get("game_id"),reason="Projection is not a finite nonnegative number"))
            continue
        volume=p.get("expected_opportunities")
        if stat in YARD_MARKETS and isinstance(volume,(int,float)) and math.isfinite(volume):
            if stat=="passing_yards" and p.get("position")=="QB" and volume<20 and p.get("games_used",0)>=3:
                flags.append(dict(severity="warning",code="qb_low_attempts",player=name,stat_key=stat,game_id=p.get("game_id"),reason=f"QB projected {volume:.1f} attempts; check starting role"))
            if stat=="receiving_yards" and volume<3 and value>80:
                flags.append(dict(severity="warning",code="receiver_volume_mismatch",player=name,stat_key=stat,game_id=p.get("game_id"),reason=f"{value:.1f} receiving yards on {volume:.1f} targets"))
            if stat=="rushing_yards" and volume<5 and value>70:
                flags.append(dict(severity="warning",code="rusher_volume_mismatch",player=name,stat_key=stat,game_id=p.get("game_id"),reason=f"{value:.1f} rushing yards on {volume:.1f} carries"))
        if stat in YARD_MARKETS and p.get("games_used",0)>=3:
            baseline=p.get("last_5_avg")
            if isinstance(baseline,(int,float)) and baseline>=20 and (value>2.3*baseline or value<0.40*baseline):
                flags.append(dict(severity="warning",code="large_history_deviation",player=name,stat_key=stat,game_id=p.get("game_id"),reason=f"Projection {value:.1f} vs last-five {baseline:.1f}; role/injury changes may explain this"))
        if p.get("qb_workload_method")=="established_full_game_appearances_not_verified_starter":
            flags.append(dict(severity="info",code="qb_starter_unverified",player=name,stat_key=stat,game_id=p.get("game_id"),reason="Full-game workload is conditional; starting QB has not been independently verified"))
    # Multiple QB forecasts may be legitimate alternative starter scenarios.
    for (game,team),rows in by_game.items():
        qbs=[p for p in rows if p.get("stat_key")=="passing_yards" and p.get("position")=="QB" and p.get("expected_opportunities",0)>=20]
        if len(qbs)>1:
            flags.append(dict(severity="warning",code="multiple_qb_starter_scenarios",player=", ".join(str(p.get("player")) for p in qbs),stat_key="passing_yards",game_id=game,reason=f"{team}: {len(qbs)} QBs have starter-sized workloads; treat as alternative scenarios, not simultaneous predictions"))
    counts={s:sum(f["severity"]==s for f in flags) for s in ("error","warning","info")}
    return {"generated_at_utc":datetime.now(timezone.utc).isoformat(),"players_checked":len(players),"summary":counts,"flags":flags,"method":"Conservative heuristics; warnings are not verified errors; no projections altered"}

def main():
    data=json.loads(Path("data/player-research.json").read_text())
    report=audit(data.get("players"))
    path=Path("data/projection-audit.json")
    path.write_text(json.dumps(report,indent=2)+"\n")
    print(f"Audited {report['players_checked']} forecasts: {report['summary']}")
    if report["summary"]["error"]:
        raise ValueError(f"Projection audit found {report['summary']['error']} structural errors")

if __name__=="__main__":
    main()
