# Automated free-data research refresh

The GitHub Actions workflow `free-nfl-research-refresh.yml` downloads public
schedule and player-weekly CSV snapshots, runs both research forecast generators,
and uploads run summaries, score projections, player yards and player backtest
reports as **Actions artifacts**.

Runs Tuesday, Thursday, Saturday and Sunday UTC; manual dispatch can specify
season and week. The scheduled job picks the earliest upcoming regular-season
week from the schedule's Eastern-time kickoffs. Missing, malformed, or lagging
source data causes a failed run; no stale data is silently promoted.

**Safety:** read-only GitHub permissions; never commits or changes
`data/live-v2.json`, `data/player-research.json`, or `data/simulations.json`.
The reports are uncalibrated baselines, not production model predictions or
DraftKings betting edges. Before publishing, validate historical backtests
against baselines, ensure current-week active player coverage and injuries,
preserve timestamped pregame archives, and adapt all dashboard schemas.
