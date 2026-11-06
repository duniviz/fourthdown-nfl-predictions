"""Import verified official T-15 game locks into the weekly ML research archive.

Only the incumbent is imported. Challenger predictions must be independently
frozen before kickoff; this bridge never fabricates or backfills them.
"""
import json
from datetime import timedelta
from pathlib import Path
from live.game_pregame_observations import dt

def merge(locks, existing):
    indexed = {(str(r["game_id"]), str(r["player_id"]), str(r["stat_key"]), str(r["model"])): r
               for r in existing}
    added = 0
    rejected = 0
    for lock in locks:
        if lock.get("lock_status") != "official":
            rejected += 1
            continue
        kickoff = dt(lock.get("kickoff_utc"))
        forecast = dt(lock.get("forecast_at_utc"))
        quote = dt(lock.get("dk_at_utc"))
        captured = dt(lock.get("captured_at_utc"))
        cutoff = dt(lock.get("lock_cutoff_utc"))
        if (not all((kickoff, forecast, quote, captured, cutoff))
                or cutoff != kickoff - timedelta(minutes=15)
                or not all(cutoff-timedelta(minutes=90) <= t <= cutoff for t in (forecast, quote))
                or captured > cutoff or not lock.get("game_id")):
            rejected += 1
            continue
        for market, field, dkfield in (
            ("game_total", "projected_total", "dk_total"),
            ("game_margin_home", "projected_margin_home", "dk_home_spread"),
        ):
            value = lock.get(field)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            key = (str(lock["game_id"]), "GAME", market, "live")
            if key in indexed:
                continue
            indexed[key] = {
                "game_id": key[0], "player_id": "GAME", "stat_key": market,
                "model": "live", "projection": value,
                "dk_line": lock.get(dkfield),
                "kickoff_utc": kickoff.isoformat(),
                "predicted_at_utc": forecast.isoformat(),
                "source": "official T-15 game pregame lock",
                "actual": None,
            }
            added += 1
    return sorted(indexed.values(), key=lambda r: (
        str(r["game_id"]), str(r["player_id"]), str(r["stat_key"]), str(r["model"])
    )), added, rejected

def main():
    root = Path(__file__).resolve().parents[1] / "data"
    source = root / "game-official-pregame-locks.json"
    archive = root / "weekly-shadow-forecasts.json"
    locks = json.loads(source.read_text()).get("records", []) if source.exists() else []
    old = json.loads(archive.read_text()).get("rows", []) if archive.exists() else []
    rows, added, rejected = merge(locks, old)
    archive.write_text(json.dumps({
        "schema_version": 2,
        "description": "Frozen pregame research forecasts; official game incumbent locks imported",
        "rows": rows,
    }, indent=2) + "\n")
    print(f"Official game incumbent ML rows added: {added}; invalid locks rejected: {rejected}; total archive rows: {len(rows)}")

if __name__ == "__main__":
    main()
