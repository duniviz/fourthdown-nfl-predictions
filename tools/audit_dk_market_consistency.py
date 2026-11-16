"""Validate published DK game markets and established pregame quote history.

Future games may be listed by the provider before their first historical quote
is archived. Once kickoff passes, missing or post-kickoff-only quote history is
an error; the check never invents odds or backfills historical records.
"""
import datetime as dt
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
UTC = dt.timezone.utc


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else None


def audit(odds, history, now):
    """Return (errors, warnings, audited_game_count), without modifying inputs."""
    errors, warnings, seen = [], [], set()
    if not isinstance(odds, dict) or not isinstance(odds.get("games"), list):
        return ["DK games payload missing or invalid"], [], 0
    if not isinstance(history, dict):
        return ["DK history payload missing or invalid"], [], 0
    if not isinstance(now, dt.datetime) or now.tzinfo is None:
        raise ValueError("Audit clock must be timezone-aware")
    now = now.astimezone(UTC)

    # Historical feeds may use either Z or +00:00 for the same kickoff.
    historical = {}
    for key, records in history.items():
        parts = key.split("|")
        if len(parts) != 3:
            continue
        away, home, raw_kickoff = parts
        kickoff = timestamp(raw_kickoff)
        if kickoff:
            historical.setdefault((away, home, kickoff), []).extend(
                records if isinstance(records, list) else []
            )

    for row in odds["games"]:
        if not isinstance(row, dict):
            errors.append("Malformed DK game row")
            continue
        home, away, raw_kickoff = (row.get(k) for k in ("home", "away", "commence_time"))
        if not all(isinstance(value, str) and value.strip() for value in (home, away, raw_kickoff)):
            errors.append(f"Incomplete game identity: {row.get('game_id')}")
            continue
        kickoff = timestamp(raw_kickoff)
        key = f"{away}|{home}|{raw_kickoff}"
        if kickoff is None:
            errors.append(f"Invalid kickoff timestamp: {key}")
            continue
        identity = (away, home, kickoff)
        if identity in seen:
            errors.append(f"Duplicate DK game: {key}")
        seen.add(identity)
        if home == away:
            errors.append(f"Same home and away team: {key}")
        spread, total = row.get("home_spread"), row.get("total")
        if spread is None and total is None:
            errors.append(f"Game without spread or total: {key}")
        for label, value, low, high in (
            ("spread", spread, -35, 35),
            ("total", total, 15, 100),
        ):
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (float, int))
                or not low <= value <= high
            ):
                errors.append(f"Invalid {label} for {key}: {value}")

        records = historical.get(identity, [])
        has_pregame_quote = any(
            (captured := timestamp(entry.get("captured_at_utc"))) is not None
            and captured < kickoff
            and (entry.get("home_spread") is not None or entry.get("total") is not None)
            for entry in records if isinstance(entry, dict)
        )
        if not has_pregame_quote:
            message = f"No saved pregame quote history: {key}"
            if kickoff > now:
                warnings.append(message + " (upcoming game, not yet required)")
            else:
                errors.append(message + " (kickoff reached; cannot grade without a saved pregame quote)")
    return errors, warnings, len(seen)


def main():
    odds = json.loads((DATA / "dk-game-odds.json").read_text(encoding="utf-8"))
    history = json.loads((DATA / "dk-game-line-history.json").read_text(encoding="utf-8")).get("games", {})
    errors, warnings, count = audit(odds, history, dt.datetime.now(UTC))
    for message in warnings:
        print(f"WARNING: {message}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"PASS: {count} unique DraftKings games, numeric market sanity and started-game pregame history. Upcoming missing history warnings: {len(warnings)}")


if __name__ == "__main__":
    main()
