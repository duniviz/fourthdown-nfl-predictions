# Verified game-day starters

`data/verified-starters.json` is the pregame source of confirmed starts for quarterbacks, running backs, and wide receivers. Add a game-specific record when the team confirms a player's starting role. Use the club's official announcement as the source; do not treat depth-chart order, recent participation, or a sportsbook line as confirmation.

Each record needs:

- `season`, `week`, and `game_id` matching the schedule
- `team`, `player`, `position` (`QB`, `RB`, or `WR`), and `status: "confirmed"`
- `source`, `source_url`, and `confirmed_at_utc`

The projection generator uses a matching confirmation to retain that player even if the recent-appearance cutoff would otherwise remove them. The published feed marks that player as `confirmed_starter` and includes the source link. For QB only, when a confirmed starter exists, a competing QB is marked `not_starting` and hidden from the pregame player card. RB and WR cards remain visible together because teams can start multiple receivers and use running-back committees; confirmed players receive a badge without labeling every teammate a backup.

When there is no sourced confirmation, the app labels the player **Starter not confirmed**. It must not infer a confirmed start from depth charts or recent stats.

After adding records, run the normal player projection refresh and site publication workflow. Keep each confirmation tied to one game so a prior week's starter never carries forward. Multiple confirmed WRs or RBs are allowed for the same team and game.

The Carson Wentz Week 9 record is the example entry in the JSON file, sourced from the Vikings' announcement: https://www.vikings.com/news/quarterback-carson-wentz-monday-night-bills
