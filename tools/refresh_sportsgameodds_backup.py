#!/usr/bin/env python3
"""Conservative DraftKings-only SportsGameOdds backup; never expose the API key."""
import datetime as dt
from collections import Counter
import json
import math
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from refresh_parlayapi_odds import ABBR, TEAMS, load, save, merge_player_quotes

BASE = "https://api.sportsgameodds.com/v2/events"
MARKETS = {
    "passing_yards": "player_passing_yards",
    "rushing_yards": "player_rushing_yards",
    "receiving_yards": "player_receiving_yards",
    "passing_attempts": "player_passing_attempts",
    "passing_completions": "player_passing_completions",
    "rushing_attempts": "player_rushing_attempts",
    "receptions": "player_receptions",
}
MONTHLY_CAP = 2000
LEDGER = "sportsgameodds-usage.json"

def date(value):
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None

def finite(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError):
        return None

def team_name(value):
    if not isinstance(value, dict):
        return None
    names = value.get("names") or {}
    if not isinstance(names, dict):
        return None
    return names.get("long") or names.get("full")

def player_name(event, odd):
    # Only use a provider-supplied, unambiguous player identity.
    name = odd.get("playerName")
    if name:
        return str(name).strip()
    pid = odd.get("playerID") or odd.get("statEntityID")
    players = event.get("players") or {}
    if isinstance(players, dict):
        p = players.get(pid)
        if isinstance(p, dict):
            names = p.get("names") or {}
            return names.get("long") or names.get("full") or p.get("name")
    return None

def main():
    key = os.getenv("SPORTSGAMEODDS_API_KEY", "").strip()
    if not key:
        print("SportsGameOdds secret unavailable; backup skipped")
        return
    now = dt.datetime.now(dt.timezone.utc)
    month = now.strftime("%Y-%m")
    ledger = load(LEDGER, {})
    used = int(ledger.get("objects", 0)) if ledger.get("month") == month else 0
    # A single request can return at most 15 events; leave substantial quota headroom.
    if used + 15 > MONTHLY_CAP:
        print(f"SportsGameOdds monthly guard: {used}/{MONTHLY_CAP}; skipping")
        return
    params = urlencode({"leagueID": "NFL", "oddsAvailable": "true",
                        "finalized": "false", "includeAltLines": "false", "limit": 15})
    request = Request(BASE + "?" + params,
                      headers={"X-Api-Key": key, "Accept": "application/json",
                               "User-Agent": "FOURTHDOWN/1.0"})
    try:
        with urlopen(request, timeout=35) as response:
            payload = json.load(response)
    except Exception as exc:
        print(f"::warning::SportsGameOdds backup unavailable ({type(exc).__name__}); existing odds retained")
        return
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        print("::warning::SportsGameOdds response shape unexpected; retaining primary odds")
        return
    events = payload["data"]
    # Count every returned event even when no usable DraftKings market exists.
    save(LEDGER, {"month": month, "objects": used + len(events),
                  "last_checked_at_utc": now.isoformat()})
    game_rows, prop_rows = [], []
    diagnostics = Counter()
    diagnostics["events_returned"] = len(events)
    for event in events:
        if not isinstance(event, dict):
            continue
        teams = event.get("teams") or {}
        home = team_name(teams.get("home"))
        away = team_name(teams.get("away"))
        kickoff = date(event.get("startsAt") or event.get("startTime") or event.get("commence_time"))
        if home not in ABBR or away not in ABBR:
            diagnostics["unmatched_teams"] += 1
            continue
        if not kickoff:
            diagnostics["missing_kickoff"] += 1
            continue
        if not now < kickoff:
            diagnostics["past_events"] += 1
            continue
        diagnostics["upcoming_matched_events"] += 1
        odds = event.get("odds") or {}
        if not isinstance(odds, dict):
            continue
        game = {"game_id": event.get("eventID"), "home": ABBR[home], "away": ABBR[away],
                "home_team": home, "away_team": away, "commence_time": kickoff.isoformat(),
                "bookmaker": "draftkings", "home_spread": None, "total": None,
                "source_provider": "SportsGameOdds"}
        diagnostics["upcoming_market_rows"] += len(odds)
        for odd in odds.values():
            if not isinstance(odd, dict):
                diagnostics["invalid_market"] += 1
                continue
            diagnostics["period_" + str(odd.get("periodID"))[:24]] += 1
            diagnostics["bet_" + str(odd.get("betTypeID"))[:24]] += 1
            diagnostics["stat_" + str(odd.get("statID"))[:32]] += 1
            if odd.get("periodID") != "game":
                continue
            book = (odd.get("byBookmaker") or {}).get("draftkings")
            if not isinstance(book, dict):
                diagnostics["missing_dk_book"] += 1
                continue
            diagnostics["dk_book_present"] += 1
            if book.get("available") is not True:
                diagnostics["dk_book_unavailable"] += 1
                continue
            diagnostics["dk_book_available"] += 1
            updated = date(book.get("lastUpdatedAt"))
            if not updated or updated > now or updated >= kickoff:
                diagnostics["invalid_dk_timestamp"] += 1
                continue
            diagnostics["valid_dk_timestamp"] += 1
            stat = str(odd.get("statID") or "").lower()
            side = str(odd.get("sideID") or "").lower()
            bet = str(odd.get("betTypeID") or "").lower()
            line = finite(book.get("overUnder") if bet == "ou" else book.get("spread"))
            if bet == "ou" and side == "over" and stat in ("points", "total_points") and str(odd.get("statEntityID")).lower() == "all" and line is not None:
                game["total"] = line
                game["total_last_verified_at_utc"] = updated.isoformat()
            if bet == "sp" and side == "home" and stat in ("points", "spread") and line is not None:
                game["home_spread"] = line
                game["home_spread_last_verified_at_utc"] = updated.isoformat()
            if bet != "ou" or side != "over" or stat not in MARKETS or line is None:
                diagnostics["nonmatching_prop_market"] += 1
                continue
            diagnostics["matching_prop_market"] += 1
            player = player_name(event, odd)
            if not player or str(odd.get("statEntityID")).lower() in ("all", "home", "away"):
                diagnostics["unresolved_player"] += 1
                continue
            diagnostics["verified_prop"] += 1
            prop_rows.append({"player": player, "market_key": MARKETS[stat],
                              "line": line, "over_price": book.get("odds"),
                              "under_price": None, "home_team": home, "away_team": away,
                              "commence_time": kickoff.isoformat(),
                              "last_update": updated.isoformat(),
                              "source_provider": "SportsGameOdds"})
        if game["home_spread"] is not None or game["total"] is not None:
            game["updated_at_utc"] = max(
                (game.get(x) for x in ("home_spread_last_verified_at_utc", "total_last_verified_at_utc") if game.get(x)))
            game_rows.append(game)
    for group in ("summary", "period_", "bet_", "stat_"):
        selected = [(k, v) for k, v in diagnostics.items()
                    if (not k.startswith(("period_", "bet_", "stat_"))) == (group == "summary")
                    and (group == "summary" or k.startswith(group))]
        print("SportsGameOdds diagnostic " + group + ": " +
              ", ".join(f"{k}={v}" for k, v in sorted(selected, key=lambda x: -x[1])[:20]))
    prior_props = load("dk-odds.json", {})
    old_rows = prior_props.get("rows", [])
    # Never replace any existing exact DraftKings market from the primary feed,
    # even when the secondary provider has a newer timestamp.
    existing = {(r.get("player", "").casefold(), r.get("market_key", "").casefold(),
                 r.get("home_team"), r.get("away_team"), str(date(r.get("commence_time"))))
                for r in old_rows if isinstance(r, dict)}
    additions = [r for r in prop_rows if
                 (r["player"].casefold(), r["market_key"].casefold(), r["home_team"],
                  r["away_team"], str(date(r["commence_time"]))) not in existing]
    if additions:
        merged = merge_player_quotes(old_rows, additions, now)
        save("dk-odds.json", {**prior_props, "rows": merged})
    prior_games = load("dk-game-odds.json", {})
    by_game = {(g.get("home"), g.get("away"), str(date(g.get("commence_time")))): g
               for g in prior_games.get("games", []) if isinstance(g, dict)}
    changed = 0
    for g in game_rows:
        identity = (g["home"], g["away"], str(date(g["commence_time"])))
        old = by_game.get(identity)
        if old is None:
            by_game[identity] = g
            changed += 1
        else:
            for field in ("home_spread", "total"):
                if old.get(field) is None and g.get(field) is not None:
                    old[field] = g[field]
                    old[field + "_last_verified_at_utc"] = g.get(field + "_last_verified_at_utc")
                    changed += 1
    if changed:
        save("dk-game-odds.json", {**prior_games, "games": list(by_game.values())})
    print(f"SportsGameOdds backup: {len(events)} event objects; {len(additions)} candidate props; {changed} game market additions; monthly usage {used + len(events)}/{MONTHLY_CAP}")
    if events and not prop_rows:
        print("::warning::No fully identified standard DraftKings player props in backup response; no unverified markets published")

if __name__ == "__main__":
    main()
