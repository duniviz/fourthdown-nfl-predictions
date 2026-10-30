# Blowout and game-script dataset — research only

Run `python research/build_blowout_tendencies.py --seasons 2023 2024 2025`.

Downloads published nflverse seasonal play-by-play parquet and computes per-team, per-quarter pass/run play mix by **score differential at the snap**, avoiding final-score leakage. Output CSVs are generated locally under `reports/blowout_game_script/`; the script does not change the live site.

Source: https://github.com/nflverse/nflverse-data/releases/tag/pbp
Schema: https://py.sportsdataverse.org/docs/nfl/reference/loaders/pbp

Limitations: This is a first-pass descriptive *team-volume* dataset. It does not yet predict final player passing, rushing, or receiving yards. The next iteration should construct clock-specific snapshots and remaining-game actuals for every player, join snap/target/attempt data, validate on held-out weeks, and add team/opponent shrinkage to avoid small-sample overfitting. Current 2026 data should be included only if published and verified. Do not deploy learned factors before testing MAE/RMSE and bias against the existing score-aware formula.
