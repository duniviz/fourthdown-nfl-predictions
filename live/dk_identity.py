"""Exact identity for a DraftKings full-game quote, independent of provider IDs."""
import json
import math
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from live.game_pregame_observations import dt

CONTRACT = json.loads((Path(__file__).resolve().parents[1] / "assets/dk-markets.json").read_text())
MARKETS = {alias: key for key, aliases in CONTRACT["markets"].items() for alias in [key, *aliases]}
TEAM_CODES = {name.lower(): key for key, names in CONTRACT["teams"].items() for name in [key, *names]}

def norm(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    words = re.findall(r"[a-z0-9]+", text)
    if words and words[-1] in {"junior", "jr", "senior", "sr", "ii", "iii", "iv", "v"}:
        words.pop()
    return "".join(words)

def team(value):
    return TEAM_CODES.get(str(value or "").strip().lower())

def market(value):
    return MARKETS.get(value, value)

def finite(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None

def quote_key(q):
    return (norm(q.get("player")), market(q.get("market_key")), team(q.get("away_team")),
            team(q.get("home_team")), dt(q.get("commence_time")))

class QuoteIndex:
    def __init__(self, quotes, now):
        self.rows = defaultdict(list)
        for q in quotes:
            if q.get("bookmaker", "draftkings") != "draftkings":
                continue
            name, mk, away, home, kick = quote_key(q)
            stamp = dt(q.get("last_update"))
            line = finite(q.get("line"))
            if not all((name, mk, away, home, kick, stamp)) or home == away:
                continue
            if line is None or line <= 0 or stamp > now or stamp >= kick:
                continue
            self.rows[(name, mk, frozenset((away, home)), kick)].append((stamp, q, kick, line))

    def find(self, p, kickoff):
        key = (norm(p.get("player")), market(p.get("market_key") or p.get("market")),
               frozenset((team(p.get("team")), team(p.get("opponent")))), kickoff)
        matches = self.rows.get(key, [])
        if not matches:
            return None
        latest = max(row[0] for row in matches)
        best = [row for row in matches if row[0] == latest]
        if len({row[3] for row in best}) == 1:
            return best[0]
        return None
