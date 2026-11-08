"""Legacy CLI for the shared pregame capture."""
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from live.dk_identity import norm
from scripts.capture_pregame_snapshots import collect

ROOT = Path("data")

def main():
    collect(ROOT, datetime.now(timezone.utc))

if __name__ == "__main__":
    main()
