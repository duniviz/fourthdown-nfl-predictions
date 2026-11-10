# Verified game-day starters

`data/verified-starters.json` is the pregame source of confirmed starts for quarterbacks, running backs, and wide receivers. Add a game-specific record when the team confirms a player's starting role. Use the club's official announcement as the source; do not treat depth-chart order, recent participation, or a sportsbook line as confirmation.

Each record needs:

- `season`, `week`, and `game_id` matching the schedule
- `team`, `player`, `position` (`QB`, `RB`, or `WR`), and `status: "confirmed"`
- `source`, `source_url`, and `confirmed_at_utc`

The projection generator uses a matching confirmation to retain that player even if the recent-appearance cutoff would otherwise remove them. The published feed marks that player as `confirmed_starter` and includes the source link. For QB only, when a confirmed starter exists, a competing QB is marked `not_starting` and hidden from the pregame player card. RB and WR teammates remain visible because teams can start multiple receivers and use running-back committees.

When a sourced confirmation is absent, the card does not label a player as a starter. It must not infer a confirmed start from depth charts or recent stats.

Adding or changing a starter record on `main` automatically starts the forecast publication workflow. For upcoming games, that refresh uses the confirmed starter record to keep the player in the projection feed despite missed weeks. Keep each confirmation tied to one game so a prior week's starter never carries forward. Multiple confirmed WRs or RBs are allowed for the same team and game.

If a starter is confirmed only after kickoff, any added estimate must be labeled as a late limited-history estimate and kept separate from frozen pregame predictions. Carson Wentz's Week 9 record includes an example of that distinction.
