#!/usr/bin/env python3
"""Leakage-safe research challengers for historical NFL ATS and O/U lines."""
import json, math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "training" / "game-market-review.json"
MIN_TRAIN_GAMES, MIN_HOLDOUT_GAMES, EPS = 400, 75, 1e-9


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def build_examples(schedule):
    rows = schedule.to_dicts() if hasattr(schedule, "to_dicts") else list(schedule)
    rows.sort(key=lambda r: (int(r.get("season") or 0), int(r.get("week") or 0),
                            str(r.get("gameday") or ""), str(r.get("gametime") or "")))
    history, pending, examples = defaultdict(list), [], []
    current_week = None

    def flush():
        for key, game in pending:
            history[key].append(game)
        pending.clear()

    for row in rows:
        try:
            season, week = int(row["season"]), int(row["week"])
            group = (season, week)
            if current_week is not None and group != current_week:
                flush()
            current_week = group
            if str(row.get("game_type") or "REG") != "REG":
                continue
            home, away = row.get("home_team"), row.get("away_team")
            hs, aws = number(row.get("home_score")), number(row.get("away_score"))
            spread, total_line = number(row.get("spread_line")), number(row.get("total_line"))
            if not home or not away or home == away or None in (hs, aws, spread, total_line):
                continue
            if min(hs, aws) < 0:
                continue

            def avg(team):
                games = history[(season, team)]
                recent = games[-5:]
                if not games:
                    return [0, 22.0, 22.0, 22.0, 22.0]
                return [min(len(games), 17),
                        sum(g[1] for g in games) / len(games),
                        sum(g[2] for g in games) / len(games),
                        sum(g[1] for g in recent) / len(recent),
                        sum(g[2] for g in recent) / len(recent)]

            h, a = avg(home), avg(away)
            features = [week, *h, *a, h[1] - h[2], a[1] - a[2],
                        h[1] - a[2], a[1] - h[2]]
            margin, total = hs - aws, hs + aws
            ats_residual, ou_residual = margin - spread, total - total_line
            examples.append({
                "season": season, "week": week, "game_id": str(row.get("game_id") or ""),
                "features": features, "ats_residual": ats_residual, "ou_residual": ou_residual,
                "home_cover": int(ats_residual > EPS), "over_hit": int(ou_residual > EPS),
                "spread_push": abs(ats_residual) <= EPS, "total_push": abs(ou_residual) <= EPS,
            })
            pending.extend([((season, home), (week, hs, aws)),
                            ((season, away), (week, aws, hs))])
        except (KeyError, TypeError, ValueError):
            continue
    flush()
    return examples


def models():
    return {
        "ridge": make_pipeline(StandardScaler(), Ridge(alpha=25.0)),
        "hist_gradient_boosting": HistGradientBoostingRegressor(
            max_iter=120, max_leaf_nodes=7, min_samples_leaf=20,
            l2_regularization=10.0, random_state=42),
        "xgboost": XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05,
            min_child_weight=15, reg_lambda=20, objective="reg:squarederror",
            random_state=42, n_jobs=1, tree_method="hist"),
    }


def summarize(records, predictions, target_key, push_key):
    actual = np.asarray([row[target_key] for row in records], dtype=float)
    line_mae = float(np.mean(np.abs(actual)))
    non_push = np.abs(actual) > EPS
    sides = actual[non_push] > 0
    majority = max(float(np.mean(sides)), float(1.0 - np.mean(sides))) if sides.size else None
    result = {
        "games": len(records), "pushes": sum(bool(row[push_key]) for row in records),
        "market_line_residual_mae": round(line_mae, 4),
        "majority_side_accuracy": round(majority, 4) if majority is not None else None,
        "models": {},
    }
    for name, raw in predictions.items():
        pred = np.asarray(raw, dtype=float)
        mae = float(np.mean(np.abs(actual - pred)))
        picks = non_push & (np.abs(pred) > EPS)
        accuracy = float(np.mean((pred[picks] > 0) == (actual[picks] > 0))) if np.any(picks) else None
        result["models"][name] = {
            "residual_mae": round(mae, 4),
            "mae_improvement_vs_market_line_pct": round((line_mae - mae) / line_mae * 100, 2)
                if line_mae > 0 else None,
            "graded_picks": int(np.sum(picks)),
            "pick_accuracy": round(accuracy, 4) if accuracy is not None else None,
        }
    return result


def evaluate(examples):
    seasons = sorted({row["season"] for row in examples})
    if len(seasons) < 4:
        raise ValueError("Need at least four seasons with completed games and valid closing lines")
    targets = {"ats": ("ats_residual", "spread_push"),
               "ou": ("ou_residual", "total_push")}
    collected = {key: {"records": [], "predictions": defaultdict(list)} for key in targets}
    holdouts = []
    for season in seasons:
        train = [r for r in examples if r["season"] < season]
        test = [r for r in examples if r["season"] == season]
        if len(train) < MIN_TRAIN_GAMES or len(test) < MIN_HOLDOUT_GAMES:
            continue
        x_train = np.asarray([r["features"] for r in train], dtype=float)
        x_test = np.asarray([r["features"] for r in test], dtype=float)
        season_report = {"holdout_season": season, "training_games": len(train), "markets": {}}
        for market, (target, push) in targets.items():
            y_train = np.asarray([r[target] for r in train], dtype=float)
            preds = {}
            for name, model in models().items():
                model.fit(x_train, y_train)
                preds[name] = model.predict(x_test).tolist()
            season_report["markets"][market] = summarize(test, preds, target, push)
            group = collected[market]
            group["records"].extend(test)
            for name, values in preds.items():
                group["predictions"][name].extend(values)
        holdouts.append(season_report)
    if not holdouts:
        raise ValueError("No chronological holdout season had enough train and test games")
    aggregate = {
        market: summarize(group["records"], group["predictions"], *targets[market])
        for market, group in collected.items()
    }
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "nflverse schedules via nflreadpy",
        "line_note": "Historical lines are closing lines and are not guaranteed DraftKings-specific.",
        "feature_policy": "Prior-week team scoring and allowance history only; same-week results are withheld.",
        "target_policy": "Actual score margin/total minus closing line; pushes are separately counted.",
        "evaluation_policy": "Rolling season holdouts; each season is evaluated only against models trained on earlier seasons.",
        "research_only": True, "production_changed": False, "promoted": False,
        "aggregate": aggregate, "holdout_seasons": holdouts,
        "limitations": [
            "Historical closing lines may differ from FOURTHDOWN's timestamped DraftKings lines.",
            "This report does not alter live projections or production model weights.",
            "Candidate features omit injuries, weather, and player availability.",
        ],
    }


def main():
    import nflreadpy as nfl
    end = datetime.now(timezone.utc).year
    schedule = nfl.load_schedules(list(range(2016, end + 1)))
    report = evaluate(build_examples(schedule))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "research_only",
        "holdout_seasons": [r["holdout_season"] for r in report["holdout_seasons"]],
        "ats": report["aggregate"]["ats"], "ou": report["aggregate"]["ou"],
        "production_changed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
