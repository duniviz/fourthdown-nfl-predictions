"""Research-only public table collector. No bypass of access restrictions."""
import csv
import datetime as dt
import io
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from html.parser import HTMLParser

URLS = {
    "offensive_personnel": "https://sumersports.com/teams/offensive/personnel-tendency/",
    "offensive_formation": "https://sumersports.com/teams/offensive/formation-tendency/",
    "defensive_personnel": "https://sumersports.com/teams/defensive/personnel-tendency/",
    "defensive_formation": "https://sumersports.com/teams/defensive/formation-tendency/",
}

class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.table, self.row, self.cell = [], None, None, None
        self.depth = 0
    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table = []
            self.depth += 1
        elif self.table is not None and tag == "tr":
            self.row = []
        elif self.row is not None and tag in ("th", "td"):
            self.cell = []
    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ("th", "td") and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None and self.table is not None:
            if self.row:
                self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None
            self.depth = max(0, self.depth - 1)

def main():
    stamp = dt.datetime.now(dt.timezone.utc)
    root = Path("research/sumersports-snapshots") / stamp.strftime("%Y-%m-%d")
    root.mkdir(parents=True, exist_ok=True)
    summary = {"captured_at_utc": stamp.isoformat(), "source": "SumerSports public web tables",
               "research_only": True, "datasets": {}}
    for name, url in URLS.items():
        result = {"url": url, "status": "unavailable", "rows": 0}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FOURTHDOWN-Research/1.0 (weekly public-page validation)"})
            with urllib.request.urlopen(req, timeout=20) as response:
                html = response.read(5_000_000).decode("utf-8", errors="replace")
            parser = Tables()
            parser.feed(html)
            candidates = [t for t in parser.tables if len(t) >= 10 and len(t[0]) >= 4]
            if not candidates:
                raise ValueError("No substantial HTML table found; page may require JS or subscription")
            table = max(candidates, key=len)
            width = max(map(len, table))
            with (root / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows([r + [""] * (width - len(r)) for r in table])
            result.update(status="ok", rows=len(table)-1, columns=width)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            result["error"] = str(e)[:300]
        summary["datasets"][name] = result
    (root / "manifest.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if not any(d["status"] == "ok" for d in summary["datasets"].values()):
        raise SystemExit("No usable public HTML tables; review access or authorized export options")

if __name__ == "__main__":
    main()
