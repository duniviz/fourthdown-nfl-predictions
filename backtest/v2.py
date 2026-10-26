"""Pregame opponent-strength and recency adjusted EPA research model.

No outcome, same-week performance, or future opponent strength enters features.
Coefficients are predeclared hypotheses, not optimized on evaluation data.
"""
from collections import defaultdict
from .rolling import _number

def build_v2_predictions(schedules, team_games, min_games=3, half_life=4.0,
                         prior_weight=4.0, opponent_strength=0.5,
                         epa_to_points=45.0, home_advantage=1.5):
    if half_life <= 0 or prior_weight < 0 or not 0 <= opponent_strength <= 1:
        raise ValueError("Invalid hyperparameters")
    games_by_week = defaultdict(list)
    epa_by_game = {}
    for r in team_games:
        key = (int(r["season"]), int(r["week"]), r["team"])
        off, deff = _number(r.get("offense_epa")), _number(r.get("defense_epa"))
        if off is not None and deff is not None:
            epa_by_game[key] = (off, deff)
    for r in schedules:
        if r.get("game_type", "REG") != "REG": continue
        if _number(r.get("home_score")) is None or _number(r.get("away_score")) is None: continue
        games_by_week[(int(r["season"]), int(r["week"]))].append(r)
    # Each historical entry is adjusted at its own pregame point in time,
    # so no future opponent quality can leak backward into prior features.
    histories = defaultdict(list)
    predictions = []
    def rating(season, team, week):
        history = histories[(season, team)]
        weights = [2 ** (-(week - played_week - 1) / half_life)
                   for played_week, off, deff in history]
        denominator = prior_weight + sum(weights)
        return (
            sum(w * off for w, (_, off, _) in zip(weights, history)) / denominator,
            sum(w * deff for w, (_, _, deff) in zip(weights, history)) / denominator,
            len(history),
        )
    for season, week in sorted(games_by_week):
        # Freeze the entire week's ratings before updating any team's results.
        current = {team: rating(season, team, week) for game in games_by_week[(season, week)]
                   for team in (game["home_team"], game["away_team"])}
        for game in games_by_week[(season, week)]:
            home, away = game["home_team"], game["away_team"]
            ho, hd, hn = current[home]
            ao, ad, an = current[away]
            if hn < min_games or an < min_games: continue
            # Defense EPA is allowed EPA: higher is weaker. Matchups:
            # home attack vs away defense, away attack vs home defense.
            home_epa = ho + ad
            away_epa = ao + hd
            margin = home_advantage + epa_to_points * (home_epa - away_epa)
            total = 44.0 + epa_to_points * (home_epa + away_epa)
            actual_margin = float(game["home_score"]) - float(game["away_score"])
            predictions.append({
                "season": season, "week": week, "game_id": game["game_id"],
                "home_team": home, "away_team": away,
                "pred_margin": round(margin, 4),
                "pred_total": round(max(1.0, total), 4),
                "actual_margin": actual_margin,
                "actual_total": float(game["home_score"]) + float(game["away_score"]),
            })
        # Update after all predictions. Opponent quality comes from pregame
        # ratings, not the opponent's eventual end-of-season rating.
        for game in games_by_week[(season, week)]:
            home, away = game["home_team"], game["away_team"]
            he = epa_by_game.get((season, week, home))
            ae = epa_by_game.get((season, week, away))
            if he is None or ae is None: continue
            ho, hd, _ = current[home]
            ao, ad, _ = current[away]
            # EPA offense: remove opponent defense allowed EPA; EPA defense:
            # remove opponent offense EPA. Shrink adjustment for stability.
            histories[(season, home)].append((week,
                he[0] - opponent_strength * ad,
                he[1] - opponent_strength * ao))
            histories[(season, away)].append((week,
                ae[0] - opponent_strength * hd,
                ae[1] - opponent_strength * ho))
    return predictions
