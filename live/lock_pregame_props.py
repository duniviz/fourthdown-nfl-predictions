"""Compatibility entry point for the shared player capture pipeline."""
from datetime import datetime, timezone
from pathlib import Path
from live.dk_identity import QuoteIndex, quote_key
from scripts.capture_pregame_snapshots import collect

def match_quote(player, quotes, now):
    index = QuoteIndex(quotes, now)
    starts = {quote_key(q)[-1] for q in quotes}
    matches = [index.find(player, kick) for kick in starts if kick and now < kick]
    matches = [m for m in matches if m]
    return matches[0] if len(matches) == 1 else None

def main():
    collect(Path("data"), datetime.now(timezone.utc))

if __name__ == "__main__":
    main()
