"""Read-only pregame data quality audit. Never changes published predictions."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


def date(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except ValueError:
        return None


def audit(slate, odds, starters, now):
    errors, warnings = [], []
    games = slate.get("games") if isinstance(slate, dict) else None
    if not isinstance(games, list) or not games:
        return ["Published game slate is absent or malformed"], warnings

    upcoming = []
    for game in games:
        if not isinstance(game, dict):
            errors.append("Malformed published game entry")
            continue
        kickoff = date(game.get("kickoff_utc"))
        if not kickoff:
            errors.append("Published game has an invalid kickoff")
        elif now <= kickoff <= now + timedelta(hours=24):
            upcoming.append(game)

    if not upcoming:
        return errors, warnings

    produced = date(slate.get("generated_at_utc"))
    if not produced or produced > now + timedelta(minutes=10):
        errors.append("Published forecast generation timestamp is missing or in the future")
    elif now - produced > timedelta(hours=18):
        warnings.append("Pregame scoring forecasts are more than 18 hours old")

    market_rows = odds.get("games", []) if isinstance(odds, dict) else []
    if not isinstance(market_rows, list):
        errors.append("DraftKings game odds have a malformed games list")
        market_rows = []
    matched = 0
    fresh = 0
    for game in upcoming:
        kickoff = date(game.get("kickoff_utc"))
        same = [r for r in market_rows if isinstance(r, dict)
                and r.get("home") == game.get("home")
                and r.get("away") == game.get("away")
                and date(r.get("commence_time")) == kickoff]
        if not same:
            warnings.append(f"{game.get('game_id')}: no matching DraftKings scoring market (not fabricated)")
            continue
        matched += 1
        row = same[0]
        verified = max(filter(None, [date(row.get("home_spread_last_verified_at_utc")),
                                     date(row.get("total_last_verified_at_utc")),
                                     date(row.get("observed_at_utc"))]), default=None)
        # Snapshot observation is not proof a provider quote was freshly updated.
        quote = max(filter(None, [date(row.get("home_spread_last_verified_at_utc")),
                                  date(row.get("total_last_verified_at_utc"))]), default=None)
        if quote and quote <= now + timedelta(minutes=10) and now - quote <= timedelta(hours=12):
            fresh += 1
        else:
            warnings.append(f"{game.get('game_id')}: DK spread/total quote not verified in 12 hours")
        if verified and verified > now + timedelta(minutes=10):
            errors.append(f"{game.get('game_id')}: odds timestamp is in the future")

    if not matched:
        warnings.append("No matched DK game lines for next-24-hour slate")
    elif fresh == 0:
        warnings.append("No recently verified DK game line among matched upcoming games")

    roles = starters.get("starters", []) if isinstance(starters, dict) else []
    if not isinstance(roles, list):
        errors.append("Verified starter feed is malformed")
        roles = []
    upcoming_ids = {str(g.get("game_id")) for g in upcoming}
    qb_by_team = {}
    for player in roles:
        if not isinstance(player, dict) or player.get("position") != "QB":
            continue
        game_id = str(player.get("game_id"))
        if game_id not in upcoming_ids:
            continue
        key = (game_id, player.get("team"))
        if player.get("status") == "confirmed":
            qb_by_team[key] = qb_by_team.get(key, 0) + 1
        elif player.get("status") == "projected":
            observed = date(player.get("observed_at_utc"))
            if not observed or now - observed > timedelta(hours=72):
                warnings.append(f"{game_id}/{player.get('team')}: QB projected role older than 72h or undated")
    for key, count in qb_by_team.items():
        if count > 1:
            errors.append(f"{key[0]}/{key[1]}: multiple confirmed QB starters in feed")

    return errors, warnings


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def main():
    try:
        errors, warnings = audit(load("live-v2.json"), load("dk-game-odds.json"),
                                 load("verified-starters.json"), datetime.now(timezone.utc))
    except (OSError, ValueError, TypeError) as exc:
        print(f"::error::Pregame data audit cannot read inputs: {exc}")
        return 1
    for message in warnings:
        print(f"::warning::{message}")
    for message in errors:
        print(f"::error::{message}")
    print(f"Pregame freshness audit: {len(errors)} errors, {len(warnings)} advisory warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
