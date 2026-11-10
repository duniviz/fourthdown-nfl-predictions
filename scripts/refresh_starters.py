"""Refresh game-specific QB/RB/WR starter candidates from ESPN depth charts.

Rank-one depth-chart roles are projections, not game-day confirmations. Official
team-confirmed records already in verified-starters.json always take precedence.
"""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FEED = Path("data/verified-starters.json")
FORECAST = Path("data/live-v2.json")
POSITIONS = {"QB": 1, "RB": 2, "WR": 3}


def fetch_depth_chart(team):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team}/depthcharts"
    request = urllib.request.Request(url, headers={"User-Agent": "FOURTHDOWN starter refresh"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)
    return payload, url


def position_code(node, inherited=""):
    if not isinstance(node, dict):
        return inherited
    candidates = [
        node.get("abbreviation"), node.get("position"),
        node.get("id"), node.get("name"), node.get("shortName"),
    ]
    aliases = {
        "QUARTERBACK": "QB", "RUNNING BACK": "RB", "HALFBACK": "RB",
        "WIDE RECEIVER": "WR", "FLANKER": "WR", "SPLIT END": "WR",
    }
    for value in candidates:
        value = str(value or "").strip().upper()
        if value in POSITIONS:
            return value
        if value in aliases:
            return aliases[value]
    return inherited


def collect_depth_rows(payload):
    found = {key: [] for key in POSITIONS}

    def walk(node, current=""):
        if isinstance(node, dict):
            pos = position_code(node, current)
            athletes = node.get("athletes")
            if isinstance(athletes, list) and pos in POSITIONS:
                for chart_order, item in enumerate(athletes, 1):
                    if not isinstance(item, dict):
                        continue
                    athlete = item.get("athlete") if isinstance(item.get("athlete"), dict) else item
                    name = str(athlete.get("displayName") or athlete.get("fullName") or athlete.get("name") or "").strip()
                    rank = item.get("rank", athlete.get("rank", chart_order))
                    try:
                        rank = int(rank)
                    except (TypeError, ValueError):
                        rank = chart_order
                    if name:
                        found[pos].append((rank, name))
            for key, value in node.items():
                if key == "athletes":
                    continue
                if isinstance(value, (dict, list)):
                    walk(value, pos)
        elif isinstance(node, list):
            for value in node:
                walk(value, current)

    walk(payload)
    result = {}
    for pos, limit in POSITIONS.items():
        ordered = sorted(set(found[pos]), key=lambda row: (row[0], row[1].casefold()))
        result[pos] = [name for rank, name in ordered if rank <= limit]
    return result


def main():
    forecast = json.loads(FORECAST.read_text(encoding="utf-8"))
    games = forecast.get("games", [])
    season = int(forecast["season"])
    week = int(forecast["week"])
    now = datetime.now(timezone.utc)
    upcoming = []
    for game in games:
        try:
            kickoff = datetime.fromisoformat(str(game["kickoff_utc"]).replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            continue
        if kickoff > now:
            upcoming.append(game)

    payload = json.loads(FEED.read_text(encoding="utf-8")) if FEED.exists() else {"schema_version": 1, "starters": []}
    records = [row for row in payload.get("starters", []) if row.get("status") != "projected"]
    added = 0
    updated = 0

    for game in upcoming:
        for team in (str(game.get("home") or "").upper(), str(game.get("away") or "").upper()):
            if not team:
                continue
            try:
                chart, source_url = fetch_depth_chart(team)
                positions = collect_depth_rows(chart)
            except Exception as exc:
                print(f"Depth chart unavailable for {team}: {exc}")
                continue
            for position, names in positions.items():
                # Keep official game-specific confirmations as the authority.
                if any(row.get("game_id") == game.get("game_id") and row.get("team") == team
                       and row.get("position") == position and row.get("status") == "confirmed"
                       for row in records):
                    continue
                for rank, player in enumerate(names, 1):
                    records.append({
                        "season": season, "week": week, "game_id": game["game_id"],
                        "team": team, "player": player, "position": position,
                        "status": "projected", "depth_rank": rank,
                        "source": "ESPN depth chart",
                        "source_url": source_url,
                        "observed_at_utc": now.isoformat(),
                    })
                    added += 1
            print(f"Read {team} depth chart: " + ", ".join(
                f"{pos}={len(positions[pos])}" for pos in POSITIONS
            ))

    payload["schema_version"] = max(1, int(payload.get("schema_version", 1)))
    payload["description"] = (
        "Game-specific QB, RB, and WR roles. Official team announcements are confirmed; "
        "nightly ESPN depth chart entries are projected roles, not game-day confirmations."
    )
    payload["starters"] = records
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if not FEED.exists() or FEED.read_text(encoding="utf-8") != serialized:
        FEED.write_text(serialized, encoding="utf-8")
        updated = 1
    print(f"Starter feed saved={updated}; new projected depth rows={added}; upcoming games={len(upcoming)}")


if __name__ == "__main__":
    main()
