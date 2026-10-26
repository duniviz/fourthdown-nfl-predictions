# FOURTHDOWN NFL Predictions

Repository for the FOURTHDOWN NFL prediction model, evaluation, and website integration.

## Planned workflow

- **Sunday:** Generate timestamped predictions for all remaining Sunday and Monday NFL games.
- **Tuesday:** Grade locked predictions against actual results and evaluate candidate model improvements using leakage-free rolling out-of-sample tests.
- Adopt parameter changes only when credible held-out testing supports better accuracy or calibration; record baseline, candidate, evaluation period, and rollback path.
- Keep raw game and player statistics outside Google Sheets; use the prediction tracker for picks, results, model versions, and test summaries.

## Current status

This repository is newly initialized. **No trained prediction model, validated backtest, live data ingestion, or Netlify deployment pipeline is present yet.** These need to be implemented and verified before automatic code changes or website updates can be claimed.

## Security

Never commit API tokens, private credentials, or unlicensed third-party datasets. Use GitHub Actions secrets or equivalent for required credentials.
