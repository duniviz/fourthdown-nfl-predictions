"""Keep every observed pre-kickoff game forecast and select the closest saved lines.
Snapshots are append-only by capture timestamp; post-kickoff values never qualify.
The latest eligible snapshot becomes the official frozen evaluation record.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("data")
OBS = ROOT / "game-pregame-observations.json"
FINAL = ROOT / "game-pregame-final.json"

def dt(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (ValueError, TypeError):
        return None

def load(path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default

def number(value):
    try:
        if value is None or value == "":
            return None
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None

def game_key(game):
    return str(game.get("game_id") or "")

def line_for(game, history, now):
    kickoff = dt(game.get("kickoff_utc"))
    if not kickoff:
        return {}
    candidates = []
    for key, rows in history.items():
        parts = key.split("|")
        if len(parts) != 3 or parts[0] != game.get("home") or parts[1] != game.get("away"):
            continue
        parsed_kickoff = dt(parts[2])
        if not parsed_kickoff or abs((parsed_kickoff-kickoff).total_seconds()) > 12*3600:
            continue
        for row in rows:
            captured = dt(row.get("captured_at_utc"))
            if captured and captured < kickoff and captured <= now:
                candidates.append((captured, row))
    if not candidates:
        return {}
    # Spread and total can have different last available valid observations.
    output = {}
    for field in ("home_spread", "total"):
        valid = [(stamp, row) for stamp, row in candidates if number(row.get(field)) is not None]
        if valid:
            stamp, row = max(valid, key=lambda item: item[0])
            output[field] = number(row[field])
            output[field + "_captured_at_utc"] = stamp.isoformat()
    return output

def main():
    now = datetime.now(timezone.utc)
    forecasts = load(ROOT/"live-v2.json", {})
    history = load(ROOT/"dk-game-line-history.json", {}).get("games", {})
    observations = load(OBS, {"games": {}}).get("games", {})
    final = load(FINAL, {"games": {}}).get("games", {})
    for game in forecasts.get("games", []):
        key = game_key(game)
        kickoff = dt(game.get("kickoff_utc"))
        generated = dt(forecasts.get("generated_at_utc"))
        if not key or not kickoff or not generated:
            continue
        entries = observations.setdefault(key, [])
        # Capture forecast only if generated strictly before kickoff.
        if generated < kickoff and generated <= now and now < kickoff:
            record = {
                "game_id": key, "home": game.get("home"), "away": game.get("away"),
                "kickoff_utc": kickoff.isoformat(),
                "forecast_captured_at_utc": generated.isoformat(),
                "projected_home_score": number(game.get("projected_home_score")),
                "projected_away_score": number(game.get("projected_away_score")),
                **line_for(game, history, now),
            }
            # Preserve distinct snapshots, but don't duplicate an identical refresh.
            identity = (record["forecast_captured_at_utc"],
                        record.get("home_spread_captured_at_utc"),
                        record.get("total_captured_at_utc"))
            if not any((x.get("forecast_captured_at_utc"),
                        x.get("home_spread_captured_at_utc"),
                        x.get("total_captured_at_utc")) == identity for x in entries):
                entries.append(record)
        # Official record is closest pre-kickoff forecast, with separately
        # timestamped closest pre-kickoff spread and total observations.
        if key not in final:
            eligible = [x for x in entries if dt(x.get("forecast_captured_at_utc"))
                        and dt(x["forecast_captured_at_utc"]) < kickoff]
            if eligible:
                best = max(eligible, key=lambda x: dt(x["forecast_captured_at_utc"]))
                official = dict(best)
                for field in ("home_spread", "total"):
                    candidates = [x for x in eligible if number(x.get(field)) is not None
                                  and dt(x.get(field+"_captured_at_utc"))
                                  and dt(x[field+"_captured_at_utc"]) < kickoff]
                    if candidates:
                        latest = max(candidates, key=lambda x: dt(x[field+"_captured_at_utc"]))
                        official[field] = latest[field]
                        official[field+"_captured_at_utc"] = latest[field+"_captured_at_utc"]
                official["status"] = "frozen" if now >= kickoff else "provisional"
                if now >= kickoff:
                    official["frozen_at_utc"] = now.isoformat()
                final[key] = official
        elif final[key].get("status") == "provisional":
            if now < kickoff:
                eligible = [x for x in entries if dt(x.get("forecast_captured_at_utc"))
                            and dt(x["forecast_captured_at_utc"]) < kickoff]
                if eligible:
                    best = max(eligible, key=lambda x: dt(x["forecast_captured_at_utc"]))
                    # Retain the newest separately observed valid market fields.
                    final[key] = {**final[key], **best, "status": "provisional"}
                    for field in ("home_spread", "total"):
                        candidates = [x for x in eligible if number(x.get(field)) is not None
                                      and dt(x.get(field+"_captured_at_utc"))
                                      and dt(x[field+"_captured_at_utc"]) < kickoff]
                        if candidates:
                            latest = max(candidates, key=lambda x: dt(x[field+"_captured_at_utc"]))
                            final[key][field] = latest[field]
                            final[key][field+"_captured_at_utc"] = latest[field+"_captured_at_utc"]
            else:
                final[key]["status"] = "frozen"
                final[key]["frozen_at_utc"] = now.isoformat()
    OBS.write_text(json.dumps({"schema_version": 1, "games": observations}, indent=2)+"\n")
    FINAL.write_text(json.dumps({"schema_version": 1, "games": final}, indent=2)+"\n")
    print("Game observations:", sum(map(len, observations.values())),
          "official records:", len(final),
          "frozen:", sum(v.get("status") == "frozen" for v in final.values()))

if __name__ == "__main__":
    main()
