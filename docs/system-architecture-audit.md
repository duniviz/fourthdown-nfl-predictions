# FOURTHDOWN architecture audit

Audit baseline is repository main on November 8, 2026. Counts describe that checkout and change with subsequent runs.

## Data flow

1. `live.generate` builds game forecasts from nflverse data and published model inputs. `live.player_research` and `tools/publish_count_prop_projections.py` generate yardage and count forecasts. Weather, injury and opponent matchup feeds are separately published inputs.
2. `live.dk_game_refresh` and `tools.refresh_parlayapi_odds` ingest ParlayAPI DraftKings quotes. `tools.refresh_sportsgameodds_backup` can supplement missing DraftKings markets under its own quota. `live.dk_identity` and `assets/dk-markets.json` define server-side matching. The homepage and Prop Desk use `assets/dk-lines.js` with the shared market mapping.
3. `live.pregame_cycle` saves scoring observations, player snapshots and verified odds. `game-official-pregame-locks.json`, `pregame-snapshots.json`, `player-history.json` and `dk-pregame-lines.json` have distinct consumers and formats. The job aims to refresh around T-30 and select game locks around T-15. Earlier checkpoints reduce dependence on a single scheduled start.
4. ESPN feeds scoreboard and final-player collection. `live.player_results` grades archived player forecasts using nflverse actuals. `live.game_official_results` grades timestamped game locks using completed schedule scores. Weekly grading imports frozen incumbents and compares model forecasts on matched games and player markets.
5. The Wednesday unified cycle evaluates historical and frozen challengers. Labs consumes published reports and research artifacts. Current promotion code reports automatic production promotion disabled because deployable artifacts and production validation are not established.
6. GitHub Actions commits generated JSON to main. GitHub Pages serves the repository. Pages also rely on direct ESPN requests and have a published scoreboard fallback.

## Confirmed findings

- The November 8 CIN–ATL T-15 job did not persist a lock. Its commit step referenced a missing slate marker. The independent player-snapshot job skipped capture and still reported success. The game had begun before the matching repair ran. Its saved Kyle Pitts 43.5 quote and prior player projection existed in pregame commits. PR #436 joined these verified records on the live card. An official T-15 lock was not reconstructed.
- On the audited checkout, 1,013 player snapshots were present for remaining Week 9 games. Many snapshots had no matching verified DK line. That is forecast coverage, not evidence that the missing markets were offered by DraftKings.
- The game-results grader excluded `forecast_only`, `early_pregame` and `last_available` locks, preventing winner grading when game odds were missing. The repair accepts timestamp-valid pregame forecasts and grades ATS or total only when a valid pregame line was captured.
- Player snapshot matching previously retained an old line when a game's kickoff was revised. The repair requires a quote matching the new kickoff. Existing observations remain in player history.
- Failure alerts watched the former archive workflow name but omitted the production capture and weekly ML workflow names. The alert workflow now watches them and an independent coverage check.
- `data/backtests/player-predictions.csv` contains retrospective 2024–2025 walk-forward projections. It is not an archive of live predictions frozen before those games. The ML report now identifies it as historical research.
- The weekly frozen archive was absent on the audited default branch. A local dry run generated research count variants from current pregame snapshots. This does not establish that those variants were saved to production before a game or evaluated on finals.

## Remaining verification and risks

- The T-30/T-15 production cycle, provider responses, commit retries, site refresh and Wednesday grading require verification after those events occur. GitHub Actions starts can be delayed or dropped. An early checkpoint is not a T-15 lock.
- Identity resolution covers normalized names, suffixes, teams, market and kickoff. Initials, provider-specific nicknames and stable cross-provider IDs are not consistently supported across all site and research paths. Ambiguous identities require explicit resolution.
- Game and player data have multiple historical representations and UI paths. There are 64 workflow files, including manual and research workflows. A passing offline audit does not establish that every workflow has run or that its results are current.
- Promotion remains disabled. A safe production rollout needs comparable forward samples, a production-equivalent artifact, independent chronological evaluation and tested rollback. Research backtests must remain distinct from comparisons with live frozen predictions.
- Detailed 2016–2026 research, ESPN-to-nflverse final-stat reconciliation, mobile accessibility, every provider market and every scheduled run need further end-to-end verification. Historical weather and injury availability must be established before use as past pregame features.
