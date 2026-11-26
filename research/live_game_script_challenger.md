# Live game-script yardage challenger (research only)

The current website's experimental live estimate extrapolates elapsed-game yardage. This branch adds a **separate, non-production** challenger that adjusts *remaining* projected yards based on the player's team score differential and time elapsed. A trailing quarterback's passing opportunities are increased, while a leading quarterback's are reduced. Rushing receives the opposite adjustment; receiving follows passing as a first approximation.

The multipliers are **hypotheses**, not empirically fitted. This first implementation is deliberately bounded and does not claim increased accuracy. It does not alter the Game Center, published player projections, or production ESPN tracker.

## Validation plan
1. Collect timestamped pregame forecasts and in-game ESPN snapshots (score, quarter, clock, actual player yards, pass attempts, rush attempts, targets, and game ID), without using any final-game information as a feature.
2. Join to verified final player yardage. Split chronologically by game/week, and avoid having snapshots of the same game on both sides of a train/test split.
3. Evaluate passing, rushing, and receiving separately at quarter and score-differential buckets; compare baseline versus challenger with MAE/RMSE, bias, and sample counts.
4. Test volume-aware variants using observed attempts/targets and opponent tendencies, plus possession/drive data where reliably available.
5. Promote only if out-of-sample performance improves consistently; otherwise retain the baseline.

Run `python research/live_game_script_challenger.py` for synthetic directional checks. Call `grade([(Snapshot(...), verified_final_yards), ...])` after obtaining historical snapshots. **No historical performance has been measured yet.**
