#!/usr/bin/env python3
"""Validate independently generated forecast candidates before publication.

Candidates are produced by a separate, reproducible model command. This tool
does NOT manufacture predictions or rewrite timestamps on stale projections.
"""
import argparse
import datetime as dt
import json
import math
from pathlib import Path

MARKETS = {"Passing yards", "Rushing yards", "Receiving yards"}
def finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
def timestamp(s):
    try:
        value = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        if value.tzinfo is None:
            raise ValueError("timezone required")
        return value.astimezone(dt.timezone.utc)
    except (AttributeError, ValueError, TypeError) as exc:
        raise ValueError("invalid timestamp") from exc

def validate_games(data, now):
    if not isinstance(data, dict) or not isinstance(data.get("games"), list) or not data["games"]:
        raise ValueError("games: expected nonempty games array")
    created = timestamp(data.get("generated_at_utc"))
    if not now - dt.timedelta(minutes=10) <= created <= now + dt.timedelta(minutes=5):
        raise ValueError("games: generated_at_utc is stale or in future")
    seen = set()
    for game in data["games"]:
        gid = game.get("game_id")
        if not isinstance(gid, str) or not gid or gid in seen:
            raise ValueError("games: duplicate or missing game_id")
        seen.add(gid)
        if not all(isinstance(game.get(k), str) and game[k] for k in ("home", "away")):
            raise ValueError(f"{gid}: missing teams")
        if game["home"] == game["away"]:
            raise ValueError(f"{gid}: same home and away team")
        kickoff = timestamp(game.get("kickoff_utc"))
        if kickoff <= now:
            raise ValueError(f"{gid}: already kicked off; cannot publish new pregame prediction")
        for k in ("projected_home_score", "projected_away_score", "projected_margin_home", "projected_total"):
            if not finite(game.get(k)):
                raise ValueError(f"{gid}: missing/nonfinite {k}")
        h, a = game["projected_home_score"], game["projected_away_score"]
        if not (0 <= h <= 80 and 0 <= a <= 80):
            raise ValueError(f"{gid}: implausible scores")
        if abs(game["projected_total"] - h - a) > 1 or abs(game["projected_margin_home"] - (h-a)) > 1:
            raise ValueError(f"{gid}: inconsistent margin/total")
    return seen

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True, help="Staged live-v2.json from the real generator")
    parser.add_argument("--existing", type=Path, default=Path("data/live-v2.json"))
    args = parser.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    candidate = json.loads(args.candidate.read_text())
    candidate_games = validate_games(candidate, now)
    if args.existing.exists() and args.existing.stat().st_size:
        old = json.loads(args.existing.read_text())
        old_ids = {g["game_id"] for g in old.get("games", []) if isinstance(g, dict) and "game_id" in g}
        # Don't silently drop any still-upcoming matchup when publishing.
        old_upcoming = {g["game_id"] for g in old.get("games", []) if isinstance(g, dict)
                        and g.get("game_id") in old_ids and
                        isinstance(g.get("kickoff_utc"), str) and
                        timestamp(g["kickoff_utc"]) > now}
        if not old_upcoming.issubset(candidate_games):
            raise ValueError("candidate omits upcoming games from published forecast")
    print(f"Validated {len(candidate_games)} upcoming games; candidate is eligible for review, not auto-published.")

if __name__ == "__main__":
    main()
