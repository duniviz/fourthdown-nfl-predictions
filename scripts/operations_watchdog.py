"""Read-only FOURTHDOWN operations watchdog. Never publishes or changes predictions."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except ValueError:
        return None


def inspect(slate, locks, snapshots, now):
    """Return actionable errors, not warnings about legitimately absent DK markets."""
    errors = []
    if not isinstance(slate, dict) or not isinstance(slate.get("games"), list):
        return ["Published game slate is missing or malformed"]
    games = slate["games"]
    if not games:
        return ["Published game slate has no games"]
    kicks = [timestamp(g.get("kickoff_utc")) for g in games if isinstance(g, dict)]
    kicks = [k for k in kicks if k]
    if len(kicks) != len(games):
        errors.append("One or more games have invalid kickoff timestamps")
    # Outside the active slate window, do not alert about intentional offseason inactivity.
    active = any(abs((k - now).total_seconds()) <= 7 * 86400 for k in kicks)
    generated = timestamp(slate.get("generated_at_utc"))
    if active and (not generated or now - generated > timedelta(hours=36)):
        errors.append("Published game forecasts are missing a timestamp or more than 36 hours old")
    locks_by_id = {str(x.get("game_id")): x for x in locks if isinstance(x, dict)}
    for g in games:
        if not isinstance(g, dict):
            continue
        kickoff = timestamp(g.get("kickoff_utc"))
        if not kickoff or not kickoff <= now < kickoff + timedelta(hours=3):
            continue
        game_id = str(g.get("game_id"))
        if not game_id or game_id == "None":
            errors.append("Started game has no game_id")
            continue
        lock = locks_by_id.get(game_id, {})
        captured = timestamp(lock.get("captured_at_utc"))
        forecast = timestamp(lock.get("forecast_at_utc"))
        if not (captured and forecast and forecast <= captured < kickoff):
            errors.append(f"{game_id}: missing valid frozen pregame game forecast")
        rows = [s for s in snapshots if isinstance(s, dict)
                and str(s.get("game_id")) == game_id
                and timestamp(s.get("kickoff")) == kickoff
                and timestamp(s.get("captured_at"))
                and timestamp(s.get("saved_at_utc"))
                and timestamp(s["captured_at"]) <= timestamp(s["saved_at_utc"]) < kickoff]
        if not rows:
            errors.append(f"{game_id}: missing frozen pregame player projections")
    return errors


def load(name, key=None):
    obj = json.loads((DATA / name).read_text(encoding="utf-8"))
    return obj if key is None else obj.get(key, [])


def main():
    now = datetime.now(timezone.utc)
    try:
        errors = inspect(load("live-v2.json"), load("game-official-pregame-locks.json", "records"),
                         load("pregame-snapshots.json", "records"), now)
    except (OSError, ValueError, AttributeError, TypeError) as exc:
        errors = [f"Cannot inspect current published pipeline data: {type(exc).__name__}: {exc}"]
    if errors:
        for error in errors:
            print(f"::error::{error}")
        return 1
    print("FOURTHDOWN watchdog: active-slate freshness and started-game locks verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
