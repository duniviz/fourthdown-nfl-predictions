# Player yardage baseline and walk-forward grading

These scripts consume a locally supplied nflverse weekly-player CSV snapshot.
No API key is required. They **do not** update FOURTHDOWN's live player desk.

```bash
python tools/project_player_yards.py --weekly-csv /tmp/player_stats.csv --season 2026 --week 8 --output /tmp/player-research-8.json
python tools/backtest_player_yards.py --weekly-csv /tmp/player_stats.csv --season 2025 --first-week 5 --last-week 18
```

The projections use a weighted blend of the last five games and season
average, using only rows before the target week. At least three historical
games are required. Backtest output includes per-market MAE and sample sizes.

**Known limitations:** The weekly source may include zero-yard appearances;
injury and active-roster status, snap shares, opponent adjustments, player
trades and current-week schedule joins are not modeled. Historical test
selection conditions on having a current-week player row and therefore
does not measure inactive-player false positives. These results must NOT
be interpreted as validated betting edges. Production requires comparison
against a stronger baseline, cutoff-safe player availability, a dashboard
schema adapter, and a fail-closed publisher.
