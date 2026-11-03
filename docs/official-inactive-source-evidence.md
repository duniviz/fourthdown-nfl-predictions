# PR51: official NFL source evidence

The optional source-evidence fetcher accepts explicit `https://www.nfl.com/...` or `https://nfl.com/...` inactive-report URLs and records retrieval time, HTTP status, content type and byte length. It forbids cross-domain redirects, non-HTML responses, oversized pages and non-NFL hosts.

Example: `python tools/fetch_official_inactive_sources.py --source-url https://www.nfl.com/news/example-report --output staging/results/official-source-evidence.json`

**Not yet a player-status feed:** NFL pages can contain other players' names, outdated content, or unstructured text. A successful fetch cannot certify any particular player inactive or active. There is no automatic injury-status override. An independently validated report parser with game IDs, roster identity matching and published-at timestamps must be implemented before this source can affect eligibility.

The tool is opt-in and never guesses URLs; the scheduled workflow does not call it without real report URLs.
