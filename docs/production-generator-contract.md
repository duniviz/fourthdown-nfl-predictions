# FOURTHDOWN production forecast generator contract

**Status: NOT CONNECTED.** This repository currently has published JSON forecasts and
research scripts, but no verified reproducible command that regenerates both live
game scores and player projections. Do not treat the scheduled readiness workflow
as a forecast refresh.

## Required before automatic publication

1. Implement a deterministic production entry point, e.g.
   `python -m production.generate --as-of <UTC timestamp> --output staging/`.
2. Read historical statistics available strictly before `--as-of`, the upcoming
   schedule, and verified injury/weather information. Record data provenance.
3. Produce `staging/live-v2.json`, `staging/simulations.json`, and
   `staging/player-research.json` in their documented dashboard schemas.
4. Run `python tools/validate_forecast_candidate.py --candidate staging/live-v2.json`
   and additional player/simulation schema, provenance, freshness and coverage
   checks. Reject empty, nonfinite, post-kickoff, or stale candidates.
5. Compare against the published feed; archive immutable timestamped pregame
   versions **before** changing any public file. Never replace a locked
   pregame forecast for a game after kickoff.
6. Only after an independent historical backtest and end-to-end dry run,
   enable a narrowly scoped Actions write token and atomic publish step.
   On failure, leave all published files unchanged.

## Operator checklist

- Existing `data/live-v2.json` is a published output, **not** a training
  dataset or a generator.
- `research/v3_challenger.py` is research-only and does not replay the exact
  production engine.
- A successful readiness workflow means the checks ran; it does not prove
  that new predictions were generated.
- Auto-adjusting model weights remains disabled independently of forecast refreshes.
