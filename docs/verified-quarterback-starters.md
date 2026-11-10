# Verified quarterback starters

`data/verified-starters.json` is the pregame source of confirmed quarterback starts. Add a game-specific record when a team announces its starter. Use the club's official announcement as the source; do not treat depth-chart order, recent participation, or a sportsbook line as confirmation.

Each record needs:

- `season`, `week`, and `game_id` matching the schedule
- `team`, `player`, `position: "QB"`, and `status: "confirmed"`
- `source`, `source_url`, and `confirmed_at_utc`

The projection generator uses a matching confirmation to retain that quarterback even if the recent-appearance cutoff would otherwise remove them. The published player feed marks that QB as `confirmed_starter`; competing QBs for the same team are marked `not_starting`, so the game card can show the confirmed starter and avoid presenting an older starter as current.

When there is no sourced confirmation, the app labels a QB as **Starter not confirmed**. It must not infer a confirmed start from depth charts or recent stats.

After adding a record, run the normal player projection refresh and site publication workflow. Keep each confirmation tied to one game so a prior week's starter never carries forward.

The Carson Wentz Week 9 record is the example entry in the JSON file, sourced from the Vikings' announcement: https://www.vikings.com/news/quarterback-carson-wentz-monday-night-bills
