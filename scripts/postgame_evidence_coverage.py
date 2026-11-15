"""Read-only postgame evidence coverage audit. Never writes to production data."""
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "artifacts" / "postgame-coverage.json"


def stamp(value):
    if not isinstance(value, str):
        return None
    try:
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value.astimezone(timezone.utc) if value.tzinfo else None
    except ValueError:
        return None


def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and abs(value) < float("inf")


def valid_lock(lock, kickoff):
    if not isinstance(lock, dict):
        return False
    predicted = stamp(lock.get("forecast_at_utc"))
    captured = stamp(lock.get("captured_at_utc"))
    return bool(predicted and captured and predicted <= captured < kickoff and
                finite(lock.get("projected_margin_home")) and finite(lock.get("projected_total")))


def valid_quote(lock, kickoff):
    quote = stamp(lock.get("dk_at_utc"))
    captured = stamp(lock.get("captured_at_utc"))
    return bool(quote and captured and quote <= captured < kickoff)


def evaluate(schedules, locks, game_results, player_results, shadows, now, window_days=8):
    """Audit each recently started scheduled game, including those absent from grading."""
    if not isinstance(schedules, list) or not isinstance(locks, list):
        raise ValueError("Schedules and official lock records must be lists")
    graded = {str(r.get("game_id")): r for r in game_results if isinstance(r, dict)}
    by_lock = defaultdict(list)
    for row in locks:
        if isinstance(row, dict):
            by_lock[str(row.get("game_id"))].append(row)
    by_player = defaultdict(list)
    for row in player_results:
        if isinstance(row, dict):
            by_player[str(row.get("game_id"))].append(row)
    by_shadow = defaultdict(list)
    for row in shadows:
        if isinstance(row, dict):
            by_shadow[str(row.get("game_id"))].append(row)
    rows = []
    for game in schedules:
        if not isinstance(game, dict):
            continue
        kickoff = stamp(game.get("gameday") or game.get("kickoff_utc"))
        gid = str(game.get("game_id") or "")
        if not gid or not kickoff or not now - timedelta(days=window_days) <= kickoff <= now - timedelta(hours=4):
            continue
        home, away = game.get("home_team"), game.get("away_team")
        completed = finite(game.get("home_score")) and finite(game.get("away_score"))
        candidates = [r for r in by_lock[gid] if valid_lock(r, kickoff)
                      and r.get("home") == home and r.get("away") == away]
        lock = max(candidates, key=lambda r: stamp(r["captured_at_utc"])) if candidates else None
        issues = []
        if not completed:
            issues.append("final_score_unavailable")
        if lock is None:
            issues.append("valid_frozen_game_projection_missing")
        else:
            if lock.get("lock_status") != "official":
                issues.append("official_t15_lock_missing")
            if not valid_quote(lock, kickoff) or not finite(lock.get("dk_home_spread")):
                issues.append("frozen_dk_spread_missing")
            if not valid_quote(lock, kickoff) or not finite(lock.get("dk_total")):
                issues.append("frozen_dk_total_missing")
        if completed and gid not in graded:
            issues.append("game_grading_row_missing")
        players = by_player[gid]
        # Player coverage cannot be verified if there are no corresponding archived rows.
        if not players:
            issues.append("player_grading_evidence_missing")
        elif not any(finite(p.get("dk_line")) and finite(p.get("actual")) for p in players):
            issues.append("paired_player_actual_and_dk_line_missing")
        shadows_here = by_shadow[gid]
        if not shadows_here:
            # Game challenger may be embedded in frozen observations, but this archive alone
            # cannot prove paired challenger coverage. Do not invent a baseline.
            issues.append("paired_shadow_archive_unverified")
        rows.append({
            "game_id": gid, "kickoff_utc": kickoff.isoformat(),
            "matchup": f"{away} at {home}", "completed": completed,
            "lock_status": lock.get("lock_status") if lock else None,
            "graded": gid in graded,
            "player_result_rows": len(players),
            "shadow_rows": len(shadows_here),
            "issues": issues,
            "status": "complete" if not issues else "incomplete"
        })
    rows.sort(key=lambda r: (r["kickoff_utc"], r["game_id"]))
    counts = Counter(issue for row in rows for issue in row["issues"])
    return {
        "schema_version": 1, "generated_at_utc": now.isoformat(),
        "window_days": window_days, "read_only": True, "production_modified": False,
        "complete_games": sum(r["status"] == "complete" for r in rows),
        "audited_games": len(rows), "issues_by_type": dict(sorted(counts.items())),
        "games": rows,
        "note": "Early pregame locks are not official T-15 locks; absent player or challenger rows remain unverified, not fabricated."
    }


def read(name, key):
    data = json.loads((DATA / name).read_text(encoding="utf-8"))
    rows = data.get(key, [])
    if not isinstance(rows, list):
        raise ValueError(f"{name}: {key} must be a list")
    return rows


def render(report):
    lines = ["## Postgame evidence coverage (read-only)",
             f"Audited: {report['audited_games']} games; fully verified: {report['complete_games']}",
             "| Matchup | Status | Missing/unverified evidence |",
             "|---|---|---|"]
    for game in report["games"]:
        lines.append(f"| {game['matchup']} | {game['status']} | {', '.join(game['issues']) or 'none'} |")
    if not report["games"]:
        lines.append("No games are at least 4 hours past kickoff in the current audit window.")
    lines.append("This audit does not grade missing data, alter frozen predictions, or authorize model promotion.")
    return "\n".join(lines) + "\n"


def main():
    import nflreadpy as nfl
    now = datetime.now(timezone.utc)
    locks = read("game-official-pregame-locks.json", "records")
    season_set = {int(r["season"]) for r in locks
                  if isinstance(r, dict) and str(r.get("season", "")).isdigit()}
    live = json.loads((DATA / "live-v2.json").read_text(encoding="utf-8"))
    if str(live.get("season", "")).isdigit():
        season_set.add(int(live["season"]))
    if not season_set:
        raise ValueError("No seasons documented in local evidence")
    schedules = []
    for season in sorted(season_set):
        schedules.extend(nfl.load_schedules([season]).to_dicts())
    report = evaluate(schedules, locks, read("game-official-results.json", "rows"),
                      read("player-results.json", "rows"),
                      read("weekly-shadow-forecasts.json", "rows"), now)
    OUT.parent.mkdir(exist_ok=True, parents=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = render(report)
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fp:
            fp.write(summary)


if __name__ == "__main__":
    main()
