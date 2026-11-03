# Free NFL statistics: first production-engine building block

This is a **research-only** reproducible scoring baseline, not a game or
player forecast generator. The `tools/build_team_baseline.py` script reads
a downloaded nflverse schedule CSV, excludes all weeks at/after the specified
cutoff, computes points scored/allowed per team, and shrinks small samples
toward the league average.

Example:

```bash
curl -fL https://github.com/nflverse/nfldata/raw/master/data/games.csv -o /tmp/nflverse-games.csv
python tools/build_team_baseline.py --schedule-csv /tmp/nflverse-games.csv --season 2026 --through-week 8 --output /tmp/fourthdown-baseline.json
```

Check the dataset's actual current coverage before running. The source may
lag or change its format; a missing or incomplete source must fail safely.
No paid API key is required for this baseline.

Still required before production: validated schedule ingestion, independent
player usage and injury feeds, score/yardage projection model, time-split
backtesting, output schema adapters, pregame archives, and an atomic publisher.
Never label these baseline ratings as game predictions or automatically write
them into `data/live-v2.json`.
