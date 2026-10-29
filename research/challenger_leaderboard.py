"""Evidence-only leaderboard for FOURTHDOWN research challengers."""
import csv
import json
import math
from pathlib import Path

METRICS = {
    "winner_accuracy": 1, "winner_log_loss": -1, "winner_brier": -1,
    "spread_mae": -1, "total_mae": -1, "ats_hit_rate": 1,
    "ou_hit_rate": 1, "prop_mae": -1, "prop_hit_rate": 1,
}
SOURCE = Path("research/results")
OUTPUT = Path("research/leaderboard-output")

def load():
    records = []
    for path in sorted(SOURCE.glob("*.json")):
        try:
            value = json.loads(path.read_text())
            for entry in value if isinstance(value, list) else [value]:
                if not isinstance(entry, dict) or not isinstance(entry.get("metrics"), dict):
                    raise ValueError("Expected object with metrics dictionary")
                records.append(entry | {"source": path.name})
        except (ValueError, TypeError) as exc:
            print(f"Skipping invalid {path}: {exc}")
    return records

def valid(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)

def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records = load()
    baselines = {(r.get("window"), metric): r for r in records
                 if r.get("role") == "baseline" for metric in METRICS
                 if valid(r["metrics"].get(metric))}
    rows = []
    for record in records:
        for metric, direction in METRICS.items():
            value = record["metrics"].get(metric)
            if not valid(value):
                continue
            baseline = baselines.get((record.get("window"), metric))
            comparable = (baseline is not None and record is not baseline
                          and valid(record.get("sample_size"))
                          and record.get("sample_size") == baseline.get("sample_size")
                          and record.get("sample_size") > 0)
            base = baseline["metrics"][metric] if comparable else None
            delta = (value - base) if comparable else None
            status = ("candidate_improvement" if delta * direction > 0 else "no_improvement") if comparable else "unverified"
            rows.append({"id": record.get("id", record["source"]),
                         "window": record.get("window", ""),
                         "metric": metric, "value": value,
                         "baseline": base, "delta": delta,
                         "sample_size": record.get("sample_size", ""),
                         "status": status, "source": record["source"]})
    columns = ["id", "window", "metric", "value", "baseline", "delta", "sample_size", "status", "source"]
    with (OUTPUT / "leaderboard.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    (OUTPUT / "leaderboard.json").write_text(json.dumps({
        "records": len(records), "rows": rows,
        "warning": "Exploratory only: identical sample sizes do not prove identical fixtures. No automatic promotion."
    }, indent=2) + "\n")
    print(f"Leaderboard: {len(records)} records, {len(rows)} metric comparisons")
    if not records:
        print("No research/results/*.json evidence yet; awaiting actual test results.")

if __name__ == "__main__":
    main()
