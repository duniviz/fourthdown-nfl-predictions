"""Keep the latest observed pregame standard market independent of the rolling feed."""
from live.dk_identity import quote_key, finite, CONTRACT
from live.game_pregame_observations import dt

def archive(previous, feed, observed):
    if feed.get("bookmaker") != "draftkings":
        return previous
    by_key = {quote_key(row): row for row in previous}
    for row in feed.get("rows", []):
        key = quote_key(row)
        kickoff = key[-1]
        stamp = dt(row.get("last_update"))
        if (not all(key) or key[1] not in CONTRACT["markets"] or key[2] == key[3]
                or not stamp or not stamp <= observed < kickoff
                or not (finite(row.get("line")) or 0) > 0 or row.get("bookmaker","draftkings") != "draftkings"):
            continue
        old = by_key.get(key)
        if not old or stamp > dt(old["last_update"]):
            by_key[key] = {**row, "bookmaker":"draftkings", "observed_at_utc":observed.isoformat()}
    return list(by_key.values())
