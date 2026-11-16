# FOURTHDOWN NFL Predictions

Live site: [https://duniviz.github.io/fourthdown-nfl-predictions/index.html](https://duniviz.github.io/fourthdown-nfl-predictions/index.html)

Static GitHub Pages site for FOURTHDOWN NFL game and player-prop research. HTML, CSS, and JavaScript live at the repository root. Published feeds live in `data/`. Forecasts are research estimates: `data/live-v2.json` is marked `research_uncalibrated` and is not betting advice.

## Pages

- [index.html](index.html) — current-week game forecasts, scoreboard, and matchup views.
- [bets.html](bets.html) — Player Prop Desk. Yardage and count-stat projections next to DraftKings lines.
- [history.html](history.html) — History & Accuracy for graded, locked pregame forecasts.
- [model-lab.html](model-lab.html) — Model Lab challenger comparisons and weekly learning. Production promotion stays fail-closed until an independent replay, multiweek stability, cross-market regression, and a tested rollback all pass (`tools/ml_auto_promotion.py`).
- [pipeline-health.html](pipeline-health.html) — freshness of published feeds and recent GitHub Actions runs.

## How projections are produced

Game scores, winners, spreads, and totals come from `live/generate.py`. It reads the current-season nflverse schedule and play-by-play and writes `data/live-v2.json`. The same publish job refreshes injury reports (`live/injuries.py` → `data/injuries.json`) and yardage research (`live/player_research.py` → `data/player-research.json`).

Count-stat projections (completions, rushes, receptions) come from `tools/publish_count_prop_projections.py`, which writes `data/count-projections.json` for the season and week already published in `data/live-v2.json`.

Generating forecasts locally needs the packages in `requirements-backtest.txt`.

## Scheduled refresh and deploy

Workflows that refresh data commit the JSON and push to `main`. GitHub Pages publishes that `main` branch root on each push (`legacy` build, path `/`), which is what updates the live site.

- **Sunday game day:** `Sunday preset game-day refresh` at 8:00 AM, 11:00 AM, 2:30 PM, and 6:45 PM Central. It refreshes DraftKings lines, then runs `Publish weekly v2 forecasts`.
- **Days without a game:** `Daily DraftKings player prop refresh` around 4:00 PM Central, then `Publish weekly v2 forecasts` around 5:00 PM Central. Both scheduled runs skip a date that already has a game.
- **Monday, Thursday, Friday, and Saturday game days:** the DraftKings refresh also has an hourly schedule and runs only when a kickoff is 45–115 minutes away. A successful run can start the v2 forecast in that same window.
- **Near kickoff:** `Refresh weather before kickoff` and `Publish ESPN scoreboard backup` update weather and the scoreboard on their own schedules.
- **After games:** `Grade completed NFL game predictions at 11 PM Central` grades frozen game forecasts. `Tuesday pre-forecast evaluation` (6:00 AM Central) grades the completed player slate and records learning inputs before the next forecast.
- **Count props:** `Publish count prop projections` follows a successful v2 publish and also runs on its own Sunday/Tuesday/Thursday/Saturday schedule.

Core code is in `live/` (forecasts, injuries, odds, grading), `tools/` (count props and research publishers), `scripts/`, and `.github/workflows/`.

## Tests

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

Pull requests that touch the site also run the JavaScript and published-feed checks in `.github/workflows/site-integrity.yml`.

## Security

Never commit API tokens, private credentials, or unlicensed third-party datasets. Use GitHub Actions secrets or equivalent for required credentials.
