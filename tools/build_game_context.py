#!/usr/bin/env python3
"""Build verified, timestamped game context for the FOURTHDOWN site.

This job is intentionally descriptive: it never changes a model projection.  If an
upstream public feed is unavailable, the corresponding field is omitted rather
than inferred.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import urllib.error
import urllib.request
from typing import Any

ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch_json(url: str) -> Any | None:
    request = urllib.request.Request(url, headers={"User-Agent": "fourthdown-context/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def parse_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def team_code(value: Any) -> str:
    return str(value or "").upper()


def competitor_codes(event: dict[str, Any]) -> tuple[str, str]:
    competitors = ((event.get("competitions") or [{}])[0].get("competitors") or [])
    away = next((team_code(c.get("team", {}).get("abbreviation")) for c in competitors if c.get("homeAway") == "away"), "")
    home = next((team_code(c.get("team", {}).get("abbreviation")) for c in competitors if c.get("homeAway") == "home"), "")
    return away, home


def event_for_game(game: dict[str, Any]) -> dict[str, Any] | None:
    kickoff = parse_time(game.get("kickoff_utc"))
    if not kickoff:
        return None
    scoreboard = fetch_json(f"{ESPN}/scoreboard?dates={kickoff.strftime('%Y%m%d')}&limit=1000") or {}
    for event in scoreboard.get("events", []):
        away, home = competitor_codes(event)
        if away == team_code(game.get("away")) and home == team_code(game.get("home")):
            return event
    return None


def rest_context(team: str, kickoff: dt.datetime) -> dict[str, Any]:
    schedule = fetch_json(f"{ESPN}/teams/{team.lower()}/schedule?limit=1000") or {}
    candidates: list[tuple[dt.datetime, dict[str, Any]]] = []
    for event in schedule.get("events", []):
        event_time = parse_time(event.get("date"))
        if event_time and event_time < kickoff:
            candidates.append((event_time, event))
    if not candidates:
        return {"status": "unavailable", "source": "ESPN team schedule"}
    previous_time, previous = max(candidates, key=lambda item: item[0])
    days = max(0, round((kickoff - previous_time).total_seconds() / 86400))
    return {
        "status": "verified",
        "days_since_last_game": days,
        "bye_week": days >= 11,
        "previous_game_utc": previous_time.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "ESPN team schedule",
    }


def walk_injuries(node: Any, wanted: set[str], rows: list[dict[str, str]], inherited_team: str = "") -> None:
    if isinstance(node, list):
        for item in node:
            walk_injuries(item, wanted, rows, inherited_team)
        return
    if not isinstance(node, dict):
        return
    team = team_code(node.get("team", {}).get("abbreviation") or node.get("team", {}).get("team", {}).get("abbreviation") or inherited_team)
    athlete = node.get("athlete") or {}
    name = athlete.get("displayName") or athlete.get("fullName")
    status = node.get("status", {})
    status_text = status.get("name") or status.get("description") if isinstance(status, dict) else status
    injury_type = node.get("type", {})
    injury_text = injury_type.get("description") or injury_type.get("name") if isinstance(injury_type, dict) else injury_type
    if name and team in wanted and (status_text or injury_text):
        position = athlete.get("position", {}).get("abbreviation") or ""
        row = {"team": team, "player": str(name), "position": str(position), "status": str(status_text or "reported"), "detail": str(injury_text or "")}
        if row not in rows:
            rows.append(row)
    for value in node.values():
        walk_injuries(value, wanted, rows, team or inherited_team)


def injury_context(event: dict[str, Any] | None, away: str, home: str) -> dict[str, Any]:
    if not event or not event.get("id"):
        return {"status": "unavailable", "source": "ESPN game summary"}
    summary = fetch_json(f"{ESPN}/summary?event={event['id']}")
    if not summary:
        return {"status": "unavailable", "source": "ESPN game summary"}
    rows: list[dict[str, str]] = []
    walk_injuries(summary.get("injuries", []), {away, home}, rows)
    return {
        "status": "verified" if rows else "no_reports_returned",
        "source": "ESPN game summary",
        "event_id": str(event["id"]),
        "players": rows,
    }


def model_metrics(game: dict[str, Any]) -> dict[str, Any]:
    analysis = game.get("analysis") or {}
    home, away = analysis.get("home") or {}, analysis.get("away") or {}
    return {
        "home": {key: home.get(key) for key in ("offense_rank", "defense_rank", "offense_epa_rating", "defense_epa_rating", "recent_form")},
        "away": {key: away.get(key) for key in ("offense_rank", "defense_rank", "offense_epa_rating", "defense_epa_rating", "recent_form")},
        "scoring_edge_components": analysis.get("scoring_edge_components") or {},
    }


def build(source: pathlib.Path, output: pathlib.Path) -> None:
    payload = json.loads(source.read_text(encoding="utf-8"))
    result: dict[str, Any] = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "description": "Verified schedule and availability context. Missing feed data is intentionally left unavailable.",
        "games": {},
    }
    for game in payload.get("games", []):
        game_id = game.get("game_id")
        kickoff = parse_time(game.get("kickoff_utc"))
        if not game_id or not kickoff:
            continue
        away, home = team_code(game.get("away")), team_code(game.get("home"))
        event = event_for_game(game)
        result["games"][game_id] = {
            "kickoff_utc": game.get("kickoff_utc"),
            "rest": {"away": rest_context(away, kickoff), "home": rest_context(home, kickoff)},
            "availability": injury_context(event, away, home),
            "model_metrics": model_metrics(game),
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/live-v2.json")
    parser.add_argument("--output", default="data/game-context.json")
    args = parser.parse_args()
    build(pathlib.Path(args.input), pathlib.Path(args.output))
