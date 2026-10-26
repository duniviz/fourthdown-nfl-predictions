# FOURTHDOWN prediction engine — v0.1 research baseline

This first version simulates game scores, straight-up outcomes, home-team ATS cover and totals with 5,000 Monte Carlo draws by default. It runs on Python's standard library only.

## Run locally

```bash
python -m unittest discover -s tests -v
python -m model.run examples/sample_game.json
```

The example teams and ratings are **fictional**. Do not present their output as NFL picks.

## Inputs and conventions

- `offense`: expected points above league average, before opponent adjustment.
- `defense`: expected points prevented relative to league average (positive means stronger defense).
- `home_advantage`: additional expected points for the home team.
- `pace_factor`: multiplier on expected scoring.
- `away_adjustment`, `home_adjustment`: documented pregame point adjustments.
- `spread_home`: sportsbook spread **for the home team**, e.g. -3.5 for home favored by 3.5.
- `total_line`: sportsbook game total.

The score distribution is a correlated, rounded normal baseline; it is **not yet fit or calibrated to historical NFL results**. Simulated ties are retained rather than assigned as wins. Pushes are reported separately.

## Next implementation milestones

1. Acquire timestamped, licensed/authorized historical NFL schedules, scores, play-by-play and pregame player availability; document source and coverage.
2. Generate strictly pregame opponent-adjusted offensive/defensive EPA, pace, quarterback and injury features; use prior weeks only.
3. Train expected-points and uncertainty parameters using rolling-origin cross-validation, with separate held-out evaluation seasons.
4. Benchmark versus naive home-field, simple Elo, and sportsbook closing-line baselines; evaluate MAE, log loss, Brier score, calibration, ATS/totals results and line availability.
5. Add player usage, passing/rushing/receiving distributions, correlations and DraftKings line ingestion only when legally and technically accessible.
6. Publish versioned prediction JSON to the website after tests and source verification; never overwrite timestamped locked picks.

No API feed, scheduled GitHub Action, fitted parameters, historical backtest, player-prop engine, or automatic website refresh is implemented in v0.1.
