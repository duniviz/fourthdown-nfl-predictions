# Game-day inactive verification (PR48 foundation)

The existing nflverse injury feed can lag the upcoming week. Sleeper player-profile flags are not official game-specific reports.

This validator accepts a CSV of manually sourced *inactive claims* with columns:
`player_id,status,source_url,published_at_utc,kickoff_at_utc`.

It rejects unknown projected player IDs, non-HTTPS source links, duplicate players, non-inactive statuses, and reports outside the four-hour pre-kickoff through one-hour post-kickoff window. The current time must also be in that window.

**Crucial:** A supplied URL is not proof of an official source. This tool does not fetch the linked report or establish authenticity. Its output explicitly marks `verified_source: false`, and MUST NOT alter recommendation eligibility. A future integration must retrieve and validate an authoritative NFL/team inactive report against player IDs before the label `officially confirmed inactive` can be used.

Example invocation:
`python tools/verify_gameday_inactives.py --input path/to/claims.csv --players-json staging/results/player-projections.json --output staging/results/inactive-source-claims.json`

No data is fabricated when no official report is available.
