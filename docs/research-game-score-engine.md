# Research game score projection engine (PR26)

Uses nflverse's free schedule CSV, historical completed games strictly before
the target week, and shrunk team points-for/against baselines to produce
upcoming game scores. Requires at least three earlier games for both teams.

```bash
python tools/project_game_scores.py --schedule-csv /tmp/nflverse-games.csv --season 2026 --week 8 --output /tmp/game-research.json
```

This is a **simple uncalibrated baseline**, not the existing FOURTHDOWN v2
model. The 2-point home/away shift is a provisional assumption, **not**
a fitted coefficient. No injury/weather, player projection, model selection,
cross-validation, or pregame archival is implemented. It intentionally refuses
to write inside `data/` and is not called by a publishing workflow.

Before enabling production use: fit and backtest coefficients across prior
seasons, verify schedule kickoff and team mapping, validate candidate schema,
and integrate player yardage projections with immutable pregame snapshots.
