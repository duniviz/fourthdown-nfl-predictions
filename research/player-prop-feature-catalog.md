# Expanded player-prop matchup feature catalog

Research-only. Candidate features are NOT confirmed available in current data sources or active in production.

## Position-specific defensive allowances
For QB, RB, WR, TE separately and each applicable prop market, compute opponent yards, attempts, completions, targets, receptions and touchdowns allowed per game, per opponent play and per opportunity. Include team-week totals, opponent-adjusted rates, league rank, percentile, last 3/5/8 games, season-to-date and prior-season shrinkage. Freeze all features before kickoff.

## RB
Carries and share, designed runs, inside/outside zone and gap tendencies where sourced, yards before/after contact, missed tackles forced, explosive run rate, success rate, stuff rate, short-yardage and goal-line carries, red-zone touches, snaps, routes, targets per route, RB receiving allowance, opponent box counts, run-stop and tackling metrics, offensive line injuries, committee role, pace and expected game script.

## WR
Routes, route participation, target share, first-read targets if available, targets per route, air yards, average target depth, catchable targets, yards per route, YAC, explosive catches, slot/outside alignment, man/zone splits, press, defensive personnel, coverage matchup, opponent WR1/WR2/slot allowances, red-zone/end-zone targets, QB pressure, game script and team passing attempts.

## TE
Routes, in-line/slot/wide alignment, blocking share, targets per route, TE-specific coverage allowances, linebackers/safeties, red-zone role, target depth, personnel usage and opponent TE production.

## QB
Dropbacks, pass attempts, completions, air yards, passing yards, scramble rate, designed runs, pressure-to-sack rate, blitz rate, time to throw, man/zone coverage, deep-pass allowance, defensive pass rush, pass protection, opponent QB rushing allowance, weather and expected team pass volume.

## Cross-cutting features
Injury participation and replacement role, rest, travel, surface, stadium/roof, wind, precipitation, temperature, coaching tendencies, opponent-adjusted strength of schedule, neutral-script pace, early-down pass rate, score state, betting spread/total, opening/current lines and timestamps, uncertainty and sample coverage.

## Research experiments
- Compare player workload-only baseline versus defensive position allowance, role/usage, advanced scheme and market-anchored variants.
- Use hierarchical shrinkage for small position/team samples, capped matchup adjustments as an initial conservative challenger, then tune caps only in historical training folds.
- Compare last 3/5/8 weeks and exponentially weighted estimates; prefer rates per opportunity when opponent play volume varies.
- Test interactions such as RB routes x opponent RB target allowance, WR slot share x slot coverage allowance, QB pressure x offensive line availability.
- Evaluate per-market MAE, median absolute error, quantile coverage, line-specific hit rates, calibration and paired bootstrap uncertainty.
- Preserve player/game identifiers, source, availability timestamp, feature missingness, and prediction snapshot.
- Never treat postgame allowed rankings as pregame features; never use current-week outcomes.
- Record ablations, data coverage and drift, and reject features that add noise or fail out-of-sample.

## Rollout
1. Inventory accessible datasets and verify historical availability.
2. Build leakage-safe team-week and position-week aggregates.
3. Add source-aware feature generation with explicit missing-value handling.
4. Run 2024/2025 walk-forward backtests and completed 2026 weeks.
5. Feed evidence into challenger leaderboard and retain production model unless a challenger wins repeated held-out tests.
