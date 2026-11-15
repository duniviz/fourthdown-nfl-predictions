"""Audit paired frozen challenger evidence; diagnostics only, never promote a model."""
import json
import math
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MIN_GAME_N = 100
MIN_PLAYER_N = 300
MIN_WEEKS = 3
MIN_GAIN = 0.03
GAME_MARKETS = {"game_margin_home", "game_total"}


def number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def evaluate(evidence, shadow):
    comparisons = evidence.get("paired_challenger_comparisons", [])
    if not isinstance(comparisons, list):
        raise ValueError("Paired challenger comparisons must be an array")
    week = evidence.get("week_tested")
    if not isinstance(week, str) or not week:
        raise ValueError("Missing provenance for evaluated week")
    if evidence.get("frozen_forecasts_only") is not True or evidence.get("post_kickoff_forecasts_excluded") is not True:
        raise ValueError("Unproven pregame-only evidence: fail closed")
    coverage = shadow.get("coverage", {}) if isinstance(shadow, dict) else {}
    if not isinstance(coverage, dict):
        coverage = {}
    by_market = defaultdict(list)
    rejected = 0
    for row in comparisons:
        if not isinstance(row, dict):
            rejected += 1
            continue
        market, model, n = row.get("market"), row.get("challenger"), row.get("matched_observations")
        incumbent, challenger = row.get("production_mae"), row.get("challenger_mae")
        if (not isinstance(market, str) or not market or not isinstance(model, str) or not model
                or not isinstance(n, int) or isinstance(n, bool) or n < 1
                or not number(incumbent) or incumbent <= 0
                or not number(challenger) or challenger < 0):
            rejected += 1
            continue
        gain = (incumbent - challenger) / incumbent
        by_market[market].append({"challenger": model, "matched_observations": n,
                                  "production_mae": incumbent, "challenger_mae": challenger,
                                  "relative_mae_gain": round(gain, 6)})
    leaders = {}
    for market, entries in sorted(by_market.items()):
        # Same-market leaderboard comparisons are only meaningful on identical frozen observations.
        # The source has per-candidate matched counts but no row IDs or multiweek rollup.
        # Therefore never assert that competitors share identical row sets or qualify for promotion.
        best = min(entries, key=lambda e: (e["challenger_mae"], -e["matched_observations"]))
        required = MIN_GAME_N if market in GAME_MARKETS else MIN_PLAYER_N
        leaders[market] = {**best, "required_matched_observations": required,
                           "known_independent_weeks": 1,
                           "promotion_eligible": False,
                           "blockers": (["insufficient matched observations"] if best["matched_observations"] < required else [])
                            + ["only one evaluated week documented",
                               "identical observation IDs across models not verified",
                               "independent multiweek replay and deployable rollback not proven"]}
        if best["relative_mae_gain"] < MIN_GAIN:
            leaders[market]["blockers"].append("below 3% MAE improvement target")
    incomplete = coverage.get("incomplete_player_game_markets")
    total = coverage.get("complete_player_game_markets")
    return {"week_tested": week, "research_only": True, "production_promotion_allowed": False,
            "min_independent_weeks": MIN_WEEKS, "min_relative_mae_gain": MIN_GAIN,
            "comparisons_checked": len(comparisons), "invalid_comparisons": rejected,
            "coverage": {"complete_player_game_markets": total,
                         "incomplete_player_game_markets": incomplete,
                         "coverage_incomplete": isinstance(incomplete, int) and incomplete > 0},
            "market_leaders": leaders,
            "note": "Single-week aggregate MAEs cannot establish identical rows or multiweek stability. No live promotion."}


def summary(report):
    lines = ["## FOURTHDOWN frozen ML evidence audit",
             f"Week: {report['week_tested']}; production promotion: **BLOCKED**",
             f"Compared: {report['comparisons_checked']}; invalid: {report['invalid_comparisons']}",
             "| Market | Research leader | Paired n | MAE gain | Eligible |",
             "| --- | --- | ---: | ---: | --- |"]
    for market, row in report["market_leaders"].items():
        lines.append(f"| {market} | {row['challenger']} | {row['matched_observations']} | "
                     f"{row['relative_mae_gain'] * 100:.2f}% | No |")
    lines.append("Research rankings are provisional; identical row IDs, 3 independent weeks, "
                 "deployable artifact and rollback must be validated before production changes.")
    return "\n".join(lines) + "\n"


def main():
    evidence = json.loads((DATA / "weekly-learning-evidence.json").read_text())
    shadow_path = DATA / "model-lab-weekly-shadow.json"
    shadow = json.loads(shadow_path.read_text()) if shadow_path.exists() else {}
    report = evaluate(evidence, shadow)
    result = summary(report)
    print(result)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(result)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
            fh.write("production_promotion_allowed=false\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
