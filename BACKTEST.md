# Historical backtest — initial implementation

This is **an initial research pipeline**, not a validated forecasting system.

## Run
```bash
python -m pip install -r requirements-backtest.txt
python -m backtest.download
python -m unittest discover -s tests -v
python -m backtest.run
```

Historical seasons: 2021–2025. nflreadpy loads nflverse schedules and play-by-play EPA. Raw datasets are saved locally under gitignored `data/`, never in GitHub or the Google Sheet. Attribution: nflverse (CC-BY 4.0 for most datasets; verify each dataset license).

### Leakage controls
- Team EPA is aggregated per game and enters rolling ratings **after** that game's week has been predicted.
- Ratings reset at the start of each season; predictions require 3 earlier games per team.
- All games in a week are predicted before any game in that week updates the ratings.
- The baseline uses predeclared, **unfitted** coefficients and preseason-neutral shrinkage.

### Known limitations
- These are raw opponent-aware EPA matchups, **not** a fully opponent-adjusted rating algorithm.
- No injuries, quarterback changes, weather, rest, market timestamps, or player props yet.
- The code does not yet estimate calibrated win or ATS probabilities.
- Schedule lines may be closing lines and **must not be used as pregame features** without time verification.
- The pipeline requires running in an environment with internet access; adding code alone does not constitute a completed backtest.
- Next: run actual seasons, inspect coverage, benchmark Elo/market baselines, then fit on earlier years and test on untouched later years.
