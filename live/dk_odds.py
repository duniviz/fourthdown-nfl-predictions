"""Legacy player-only entry point for the canonical primary provider."""
from tools.refresh_parlayapi_odds import main

def fetch():
    main(props_only=True)

if __name__ == "__main__":
    fetch()
