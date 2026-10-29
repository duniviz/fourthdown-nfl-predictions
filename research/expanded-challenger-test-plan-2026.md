# Expanded FOURTHDOWN challenger testing plan

Research-only specification. Do not change production predictions or publish challengers without validated promotion.

## Candidate feature families
- Games: opponent-adjusted EPA/play, success rate, explosive play rate, early-down efficiency, red-zone and third-down regression, pace, neutral-script pass rate, drive efficiency, turnovers (regressed), special teams, Elo, opponent strength, QB availability, offensive line and pass rush, rest, travel, surface, weather, coaching changes.
- ATS: market spread, opener/current movement, consensus disagreement, home-field variation, injury-adjusted power ratings, uncertainty, key-number effects.
- Totals: drives and plays projections, pace, explosive rate, weather/wind, roof, run-pass tendencies, red-zone TD rates, defensive matchup, market total and movement.
- Passing: dropbacks, neutral pass rate, pressure/sacks, coverage shell, opponent pass funnel, receiver availability, expected attempts, completion and yards per attempt distributions.
- Rushing: projected carries, scramble share, RB committee, offensive line, defensive front, game script, red-zone usage.
- Receiving: routes, target share, air yards, target depth, coverage matchup, personnel, injuries, team pass volume, yards after catch.
- Other props: receptions, completions, attempts, touchdowns (rare-event distributions), correlated game/prop scenarios.

## Challenger algorithms
Regularized logistic/linear baseline, Elo updates, Poisson/negative-binomial count models, hierarchical Bayesian shrinkage, gradient boosting (XGBoost/LightGBM if installed), random forest, calibrated ensembles, market-prior blends, dynamic weighting and ablations. Neural nets only with enough samples and appropriate regularization.

## Evaluation rules
1. Freeze baseline and timestamp predictions; use only data available before kickoff and before the line snapshot. Store provenance, missingness, source and timestamp.
2. Walk-forward train/validate/test by week and season; evaluate 2024, 2025 and completed 2026 weeks; never random-split games or leak later injury/odds/final scores.
3. Report winner accuracy, log loss, Brier, calibration, ATS and totals hit rates at recorded lines, spread/total MAE, prop MAE, distribution coverage and calibration, sample size and bootstrap uncertainty. Track CLV and hypothetical ROI separately with recorded odds and vig.
4. Compare each challenger against the *same* baseline and games/players/markets. Segment by season, week, market, line range, favorite/underdog, injury status and data coverage.
5. Run ablation and feature importance; reject improvements from leakage, tiny samples, stale prices, duplicate players or mismatched game IDs.
6. Maintain a leaderboard with challenger ID, code SHA, feature set, data cutoff, training window, test window, metrics, confidence intervals, status and artifact links.
7. Weekly shadow run before kickoff, freeze predictions, grade after official finals, and monitor drift, data freshness, coverage, errors and calibration. Keep all challengers research-only until repeated out-of-sample improvement and manual promotion.

## Suggested execution order
First audit existing workflows, artifacts and dataset timestamps; next add data-quality checks and baseline snapshots; then feature ablations and lightweight challengers; then ensemble and prop distributions; finally weekly automated leaderboard and alerting. Avoid running every combinatorial feature combination; prioritize promising candidates and correct for multiple comparisons.

## Promotion gate
No automatic promotion. Require meaningful repeated out-of-sample improvement on primary metric, acceptable secondary metrics, sufficient sample size, no leakage, reproducible artifacts and stable weekly shadow results. Production remains unchanged.