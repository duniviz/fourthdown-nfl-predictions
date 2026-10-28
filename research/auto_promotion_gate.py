#!/usr/bin/env python3
"""Fail-closed weekly readiness gate for automated model promotion.

No production model may be changed by this gate. A separate production
integration must consume approved candidates and preserve rollback metadata.
"""
import json
import sys
from pathlib import Path

MIN_PLAYER_HOLDOUT = 200
MIN_GAME_HOLDOUT = 200
MIN_MARKET_IMPROVEMENT = 0.02

def main():
    reasons = []
    path = Path("research/v3-results/results.json")
    if not path.exists():
        reasons.append("Missing V3 holdout results")
        results = {}
    else:
        results = json.loads(path.read_text()).get("markets", {})
    for market in ("passing_yards", "rushing_yards", "receiving_yards"):
        r = results.get(market)
        if not r:
            reasons.append(f"{market}: no holdout evidence")
            continue
        if int(r.get("test_2025_n", 0)) < MIN_PLAYER_HOLDOUT:
            reasons.append(f"{market}: fewer than {MIN_PLAYER_HOLDOUT} holdout observations")
        baseline = float(r.get("baseline_2025_mae", 0))
        challenger = float(r.get("challenger_2025_mae", float("inf")))
        if baseline <= 0 or challenger > baseline * (1 - MIN_MARKET_IMPROVEMENT):
            reasons.append(f"{market}: improvement below 2% MAE threshold")
    # The V3 harness explicitly compares research formulas, not the production
    # model, and its 2025 holdout is not a final promotion evaluation.
    reasons.append("No exact production-model replay on independent chronological holdouts")\n    reasons.append("No multiweek stability and cross-market regression checks")
    reasons.append("No verified automated deployment and rollback integration")
    report = {"approved_for_auto_promotion": False, "reasons": reasons,
              "policy": "fail-closed", "candidate_markets": list(results)}
    dest = Path("research/auto-promotion")
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "readiness.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
