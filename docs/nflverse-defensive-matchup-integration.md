# nflverse defensive matchup source contract

Primary source: https://github.com/nflverse/nflverse-data/releases

## Integration decision
Use nflverse play-by-play for defensive team and opponent-player outcomes, with verified player position and completed-game schedule metadata. Do not use the frozen legacy `player_stats.parquet` (ends 2024); the maintained season-specific `stats_player` release is suitable for player recent form.

FOURTHDOWN's `index.html` already renders `opponent_position_context` and `opponent_defense_context` in `propExplanation`. Populate that **existing** schema rather than introducing a second competing explanation on the cards. The separately committed `assets/defensive-matchup-intelligence.js` is not wired into production.

## Required invariants
- Generate records only from **completed** games before the individual game's kickoff; never use same-game or future statistics.
- Attribute nflverse and retain upstream release timestamp, source URL, generation timestamp and season/week cutoff.
- Group receiving outcomes by defense + opponent player's actual position (WR, TE, RB); group rushing by defense + runner position; passing by defense + QB.
- Count a defensive game's allowed yardage once per game, including games where a position has zero production; validate team/game membership before aggregation.
- Distinguish NFL rank from-most vs from-fewest; handle ties consistently.
- Minimum three completed games for any qualitative strength label; otherwise show an unavailable statement.
- Include season and last-five completed-game averages, sample counts, and league comparison where verifiable.
- Do not infer player-specific target share or coverage assignments from team-level allowed yards.
- Freeze matchup explanations with the existing 30-minute pregame snapshot; do not overwrite archived explanations with later data.
- On upstream failure, retain last *timestamped* successful verified data, clearly mark it stale, or hide the claim; never manufacture figures.
- No edits to projections, formulas, DraftKings lines, rankings, grading, picks or simulations.

## Acceptance tests before merge
1. Cross-check at least one QB, RB, WR and TE defensive matchup against raw completed games.
2. Validate zero-production games, byes, team changes, ties and unavailable position.
3. Assert existing prediction and DK JSON files byte-identical to base branch.
4. Assert existing cards display the new source-backed explanation without duplicate blocks.
5. Confirm mobile display and GitHub Pages deployment, then mark PR ready and merge only after tests pass.

Source/license: nflverse data generally CC BY 4.0; check dataset-specific license before redistribution. https://github.com/nflverse
