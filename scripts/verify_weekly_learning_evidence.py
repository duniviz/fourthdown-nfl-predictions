"""Create auditable weekly evidence from exact frozen pregame/final-result matches."""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def week_key(game_id):
    parts = str(game_id).split("_")
    return (parts[0], parts[1]) if len(parts) >= 4 else None


def finite(value):
    try:
        number = float(value)
        return number if number == number and abs(number) != float("inf") else None
    except (TypeError, ValueError):
        return None


def build_evidence(forecasts, player_results, game_results, generated_at=None):
    actuals = {}
    for row in player_results:
        if row.get("actual") is None or row.get("dnp") or row.get("played") is False:
            continue
        key = (str(row.get("game_id")), str(row.get("player_id")), str(row.get("stat_key")))
        actual = finite(row.get("actual"))
        if all(key) and actual is not None:
            actuals[key] = actual

    by_model = defaultdict(dict)
    for row in forecasts:
        game_id = str(row.get("game_id"))
        wk = week_key(game_id)
        if not wk:
            continue
        kickoff = row.get("kickoff_utc")
        predicted = row.get("predicted_at_utc")
        try:
            kick = datetime.fromisoformat(str(kickoff).replace("Z", "+00:00"))
            pred = datetime.fromisoformat(str(predicted).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if pred.tzinfo is None or kick.tzinfo is None or pred >= kick:
            continue
        player_id = str(row.get("player_id"))
        market = str(row.get("stat_key"))
        model = str(row.get("model"))
        prediction = finite(row.get("projection"))
        if not all((player_id, market, model)) or prediction is None:
            continue
        key = (game_id, player_id, market)
        by_model[key][model] = prediction

    player_keys = {key for key in by_model if key[1] != "GAME" and key in actuals and "live" in by_model[key]}
    completed_games = {}
    for row in game_results:
        game_id = str(row.get("game_id"))
        if not week_key(game_id) or finite(row.get("home_score")) is None or finite(row.get("away_score")) is None:
            continue
        completed_games[game_id] = row
    completed_weeks = {week_key(game_id) for game_id in completed_games}
    if not completed_weeks:
        raise ValueError("No completed games are available for weekly evaluation")
    selected_week = max(completed_weeks, key=lambda wk: (int(wk[0]), int(wk[1])))

    selected_players = [key for key in player_keys if week_key(key[0]) == selected_week]
    selected_games = [row for game_id, row in completed_games.items() if week_key(game_id) == selected_week]
    if not selected_players or not selected_games:
        raise ValueError(f"Prior week {selected_week} is missing matched player or game records")

    paired = defaultdict(list)
    for key in selected_players:
        actual = actuals[key]
        live = by_model[key]["live"]
        for model, projection in by_model[key].items():
            if model != "live":
                paired[(key[2], model)].append((abs(live - actual), abs(projection - actual)))

    game_actuals = {}
    for row in selected_games:
        gid = str(row["game_id"])
        game_actuals[(gid, "GAME", "game_margin_home")] = finite(row["home_score"]) - finite(row["away_score"])
        game_actuals[(gid, "GAME", "game_total")] = finite(row["home_score"]) + finite(row["away_score"])
    for key, actual in game_actuals.items():
        values = by_model.get(key, {})
        if "live" not in values:
            continue
        for model, prediction in values.items():
            if model != "live":
                paired[(key[2], model)].append((abs(values["live"] - actual), abs(prediction - actual)))

    comparisons = []
    for (market, model), values in sorted(paired.items()):
        n = len(values)
        comparisons.append({
            "market": market,
            "challenger": model,
            "matched_observations": n,
            "production_mae": round(sum(x[0] for x in values) / n, 4),
            "challenger_mae": round(sum(x[1] for x in values) / n, 4),
        })
    if not comparisons:
        raise ValueError(f"Week {selected_week} has no frozen incumbent/challenger pairs")

    return {
        "generated_at_utc": (generated_at or datetime.now(timezone.utc)).isoformat(),
        "week_tested": f"{selected_week[0]}_week_{int(selected_week[1])}",
        "matched_player_game_markets": len(selected_players),
        "completed_games_tested": len(selected_games),
        "paired_challenger_comparisons": comparisons,
        "frozen_forecasts_only": True,
        "verified_player_results_source": "data/player-results.json",
        "verified_game_results_source": "data/game-official-results.json",
        "forecast_archive_source": "data/weekly-shadow-forecasts.json",
        "post_kickoff_forecasts_excluded": True,
    }


def main():
    data = ROOT / "data"
    forecasts = json.loads((data / "weekly-shadow-forecasts.json").read_text()).get("rows", [])
    player_results = json.loads((data / "player-results.json").read_text()).get("rows", [])
    game_results = json.loads((data / "game-official-results.json").read_text()).get("rows", [])
    evidence = build_evidence(forecasts, player_results, game_results)
    out = data / "weekly-learning-evidence.json"
    out.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
