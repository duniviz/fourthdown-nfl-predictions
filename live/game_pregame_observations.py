"""Archive verified pre-kickoff game forecasts and DraftKings lines without API calls.

Observations are append-only. A later grading step must select one official
snapshot per game; never treat all observations as independent games.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("data")
OUT = ROOT / "game-pregame-observations.json"

def dt(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (ValueError, TypeError):
        return None

def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None

def collect(forecasts, odds, existing, now):
    saved = list(existing)
    seen = {(r.get("game_id"), r.get("forecast_at_utc"), r.get("dk_at_utc"))
            for r in saved if isinstance(r, dict)}
    quotes = {}
    for q in odds:
        if not isinstance(q, dict) or str(q.get("bookmaker", "")).lower() != "draftkings":
            continue
        kickoff = dt(q.get("commence_time"))
        observed = dt(q.get("observed_at_utc") or q.get("updated_at_utc"))
        if not kickoff or not observed or not observed <= now < kickoff:
            continue
        key = (str(q.get("away")), str(q.get("home")), kickoff)
        if key not in quotes or observed > quotes[key][0]:
            quotes[key] = (observed, q)
    for g in forecasts:
        kickoff = dt(g.get("kickoff_utc"))
        forecast_at = dt(g.get("_forecast_generated_at"))
        if not kickoff or not forecast_at or not forecast_at <= now < kickoff:
            continue
        match = quotes.get((str(g.get("away")), str(g.get("home")), kickoff))
        if not match:
            continue
        observed, quote = match
        spread, total = number(quote.get("home_spread")), number(quote.get("total"))
        margin, projected_total = number(g.get("projected_margin_home")), number(g.get("projected_total"))
        market_observations=[dt(quote.get(field+"_observed_at_utc") or quote.get("observed_at_utc") or quote.get("updated_at_utc"))
                             for field,value in (("home_spread",spread),("total",total)) if value is not None]
        if not market_observations or any(value is None for value in market_observations):
            continue
        # If both game markets are published, the observation is only as fresh
        # as the older of the two verified markets.
        observed=min(market_observations)
        if margin is None or projected_total is None or (spread is None and total is None):
            continue
        key = (str(g.get("game_id")), forecast_at.isoformat(), observed.isoformat())
        if key in seen:
            continue
        saved.append({
            "game_id": key[0], "season": g.get("season"), "week": g.get("week"),
            "home": g.get("home"), "away": g.get("away"),
            "kickoff_utc": kickoff.isoformat(),
            "forecast_at_utc": key[1], "dk_at_utc": key[2],
            "captured_at_utc": now.isoformat(),
            "predicted_winner": g.get("predicted_winner"),
            "projected_margin_home": margin, "projected_total": projected_total,
            "dk_home_spread": spread, "dk_total": total,
            "dk_home_spread_updated_at_utc": quote.get("home_spread_last_verified_at_utc") or quote.get("updated_at_utc"),
            "dk_total_updated_at_utc": quote.get("total_last_verified_at_utc") or quote.get("updated_at_utc"),
            "dk_home_spread_observed_at_utc": quote.get("home_spread_observed_at_utc") or quote.get("observed_at_utc") or observed.isoformat(),
            "dk_total_observed_at_utc": quote.get("total_observed_at_utc") or quote.get("observed_at_utc") or observed.isoformat(),
            "source": quote.get("source_provider") or "DraftKings"
        })
        saved[-1].update({k:g[k] for k in ("projected_home_score","projected_away_score") if k in g})
        seen.add(key)
    return saved

def main():
    now = datetime.now(timezone.utc)
    forecast = json.loads((ROOT / "live-v2.json").read_text())
    odds = json.loads((ROOT / "dk-game-odds.json").read_text())
    old = json.loads(OUT.read_text()) if OUT.exists() else {"records": []}
    games = [{**g, "_forecast_generated_at": forecast.get("generated_at_utc")}
             for g in forecast.get("games", [])]
    records = collect(games, odds.get("games", []), old.get("records", []), now)
    OUT.write_text(json.dumps({"schema_version": 1, "records": records}, indent=2) + "\n")
    print(f"Saved {len(records)} game pregame observations")

if __name__ == "__main__":
    main()
