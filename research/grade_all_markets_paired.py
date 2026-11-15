#!/usr/bin/env python3
"""All-market paired frozen forecasting research across completed NFL weeks.

Production predictions, model selection and archived observations are untouched.
Never reconstruct a forecast after kickoff or declare promotion eligibility.
"""
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
from same_slate_leaderboard import finite, timestamp
from join_frozen_pregame_results import norm
from grade_yardage_game_models import get_game_actuals

GAME_ID = re.compile(r"^(\\d{4})_(\\d{1,2})_[^_]+_[^_]+$")
GAME_MARKETS = {"game_margin_home", "game_total"}


def grade(forecasts, actuals):
    groups = defaultdict(dict)
    duplicates = set()
    rejected = defaultdict(int)
    for row in forecasts:
        if not isinstance(row, dict):
            rejected["malformed_forecast"] += 1
            continue
        market = norm(row.get("stat_key"))
        game_id = str(row.get("game_id") or "")
        player = str(row.get("player_id") or "")
        model = str(row.get("model") or "")
        match = GAME_ID.fullmatch(game_id)
        key = (game_id, player, market)
        kickoff = timestamp(row.get("kickoff_utc"))
        predicted = timestamp(row.get("predicted_at_utc"))
        value = finite(row.get("projection"))
        if (not match or not 1 <= int(match.group(2)) <= 22 or not player or not market
                or not model or not kickoff or not predicted or predicted >= kickoff
                or value is None or not math.isfinite(value)):
            rejected["invalid_or_postkickoff"] += 1
            continue
        identity = (key, model)
        if identity in duplicates:
            rejected["duplicate_model"] += 1
        elif model in groups[key]:
            # Fail closed for *every* occurrence after the first, not only the second.
            groups[key].pop(model)
            duplicates.add(identity)
            rejected["duplicate_model"] += 1
        else:
            groups[key][model] = value

    paired = defaultdict(list)
    for key, models in groups.items():
        actual = finite(actuals.get(key))
        if actual is None:
            continue
        incumbent = models.get("live")
        if incumbent is None:
            rejected["missing_frozen_live"] += 1
            continue
        week_match = GAME_ID.fullmatch(key[0])
        week = f"{week_match.group(1)}_{int(week_match.group(2)):02d}"
        for challenger, pred in models.items():
            if challenger == "live":
                continue
            paired[(key[2], challenger)].append((week, abs(incumbent-actual), abs(pred-actual)))

    scores = []
    for (market, challenger), rows in sorted(paired.items()):
        by_week = defaultdict(list)
        for week, live_error, challenger_error in rows:
            by_week[week].append((live_error, challenger_error))
        week_results = []
        for week, errors in sorted(by_week.items()):
            incumbent = sum(x[0] for x in errors) / len(errors)
            candidate = sum(x[1] for x in errors) / len(errors)
            week_results.append({
                "week": week, "matched_observations": len(errors),
                "live_mae": round(incumbent, 4), "challenger_mae": round(candidate, 4),
                "challenger_better": candidate < incumbent,
            })
        n = len(rows)
        live = sum(x[1] for x in rows) / n
        candidate = sum(x[2] for x in rows) / n
        gain = (live-candidate)/live if live > 0 else None
        winning_weeks = sum(x["challenger_better"] for x in week_results)
        required_n = 100 if market in GAME_MARKETS else 300
        enough_data = n >= required_n and len(week_results) >= 3
        consistent = winning_weeks >= math.ceil(len(week_results) * 2 / 3)
        recent = week_results[-2:]
        recent_nonregression = all(x["challenger_better"] for x in recent)
        research_thresholds_met = bool(enough_data and consistent and recent_nonregression
                                       and gain is not None and gain >= 0.03)
        blockers = []
        if n < required_n:
            blockers.append(f"need {required_n} matched frozen observations; have {n}")
        if len(week_results) < 3:
            blockers.append("need at least three independent completed weeks")
        if not consistent:
            blockers.append("challenger did not beat live in at least two-thirds of weeks")
        if not recent_nonregression:
            blockers.append("challenger did not beat live in both latest paired weeks")
        if gain is None or gain < 0.03:
            blockers.append("combined paired MAE gain below 3%")
        scores.append({
            "market": market, "challenger": challenger,
            "matched_observations": n, "independent_weeks": len(week_results),
            "winning_weeks": winning_weeks,
            "live_mae": round(live, 4), "challenger_mae": round(candidate, 4),
            "relative_improvement": round(gain, 5) if gain is not None else None,
            "weekly_results": week_results,
            "research_thresholds_met": research_thresholds_met,
            "research_blockers": blockers,
            "promotion_eligible": False,
        })
    return {
        "status": "ALL_MARKETS_PAIRED_FROZEN_FORECASTS", "research_only": True,
        "production_modified": False, "auto_promotion_enabled": False,
        "scores": scores, "rejected": dict(rejected),
        "note": "Only equal frozen game/player/market keys are paired per challenger. "
                "Research thresholds do not prove deployability or permit promotion."
    }


def main():
    data = ROOT / "data"
    forecasts = json.loads((data/"weekly-shadow-forecasts.json").read_text()).get("rows", [])
    results = json.loads((data/"player-results.json").read_text()).get("rows", [])
    actuals, conflicts = {}, set()
    for row in results:
        if (not isinstance(row, dict) or not row.get("player_id") or row.get("actual") is None
                or row.get("dnp") or row.get("played") is False):
            continue
        key = (str(row.get("game_id")), str(row["player_id"]), norm(row.get("stat_key")))
        value = finite(row["actual"])
        if value is None:
            continue
        if key in actuals and actuals[key] != value:
            conflicts.add(key)
        actuals[key] = value
    actuals.update(get_game_actuals(forecasts))
    for key in conflicts:
        actuals.pop(key, None)
    report = grade(forecasts, actuals)
    report["rejected"]["conflicting_player_actuals"] = len(conflicts)
    out = ROOT/"research"/"all-markets-paired-results"
    out.mkdir(parents=True, exist_ok=True)
    (out/"report.json").write_text(json.dumps(report, indent=2)+"\n")
    lines = ["# All markets: frozen live vs challenger on identical observations", "",
             "All available archived completed weeks; no hindsight backfills.", "",
             "| Market | Challenger | Paired n | Weeks | Winning weeks | Live MAE | Challenger MAE | Gain | Research threshold |",
             "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for x in report["scores"]:
        gain = "—" if x["relative_improvement"] is None else f'{100*x["relative_improvement"]:.2f}%'
        lines.append(f'| {x["market"]} | {x["challenger"]} | {x["matched_observations"]} | '
                     f'{x["independent_weeks"]} | {x["winning_weeks"]} | {x["live_mae"]} | '
                     f'{x["challenger_mae"]} | {gain} | '
                     f'{"passed (research only)" if x["research_thresholds_met"] else "not met"} |')
    if not report["scores"]:
        lines.append("Awaiting matched frozen forecasts and verified final results.")
    lines += ["", "Research only; no automatic deployment or production changes.",
              "Passing a research threshold does NOT establish production safety or rollback."]
    (out/"RESULTS.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
