# FOURTHDOWN Challenger Research Protocol

Status: experimental; not a verified model improvement. Do not promote to production without results.

## Baselines
- Snapshot the currently deployed game and prop prediction outputs, their version IDs, and timestamped pre-kickoff inputs.
- If executable V2/V3 code or historical predictions are unavailable, mark the baseline **unavailable**; never substitute an invented baseline.

## Candidate features
- Games: opponent-adjusted EPA/play, early-down success rate, explosive play rate, neutral pass rate, pace, offensive line vs pass rush, rest/travel, weather, injury-adjusted QB strength, and pregame consensus market spread/total.
- Props: projected team plays, dropbacks, route participation, targets per route, rush share, red-zone usage, opponent scheme, injury-driven role changes, and weather.
- Record data source, publication time, missingness, and permitted availability cutoff for every feature.

## Models
1. Regularized linear/logistic baseline with Elo and home advantage.
2. Gradient-boosted trees for game scoring and player volume/efficiency.
3. Market-anchored residual model with calibrated probabilities.
4. Stacked ensemble only if strictly nested temporal validation improves held-out results.

## Evaluation
- Rolling-origin backtests over 2024, 2025, and completed 2026 games; never train on future weeks.
- Keep the latest untouched contiguous weeks for final evaluation; fit all imputers, scalers, feature selectors, and calibration on training folds only.
- Compare same fixtures, markets, timestamps and data availability across models.
- Games: winner log loss, Brier score, calibration, score/spread/total MAE; against-spread and over/under hit rate where historical closing lines exist.
- Props: MAE by market, calibrated over/under probabilities, coverage and hit rate at recorded historical lines.
- Bets: ROI and CLV with timestamped available odds, vig, limits and realistic selection rules; report sample sizes, uncertainty intervals and drawdowns. Never infer profitable betting from hit rate alone.
- Perform paired bootstrap by game/week and compare against naive market-only and simple rolling-average baselines.

## Promotion gate
- No live site changes or automatic merge.
- Require consistent improvement in primary held-out metrics, adequate sample size, acceptable calibration, and no material regression in key subgroups.
- Publish a machine-readable comparison containing baseline version, challenger commit, cutoff timestamps, number of games/props, metrics, confidence intervals, and known limitations.
- If no candidate wins, retain the current live model.

## Next implementation milestones
1. Inventory repo scripts, workflows, data and existing research artifacts.
2. Establish reproducible baseline snapshots.
3. Add feature pipeline and source provenance.
4. Add rolling backtest runner and CI artifact generation.
5. Run and review results; propose a separate production PR only if promotion gate passes.
