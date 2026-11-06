"""Read-only FOURTHDOWN system audit; no external network or paid API calls."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
results = []
def record(name, status, detail):
    results.append((name, status, detail.replace("|", "/").replace("\n", " ")[:300]))
def run(name, command):
    proc = subprocess.run(command, capture_output=True, text=True, timeout=180)
    tail = (proc.stdout + "\n" + proc.stderr).strip().splitlines()[-5:]
    record(name, "PASS" if proc.returncode == 0 else "FAIL", "; ".join(tail) or "No output")
    return proc.returncode == 0

groups = [
    ("Kickoff and T-15 scheduling", ["tests.test_pregame_capture_guard"]),
    ("Frozen game locks", ["tests.test_game_official_pregame_locks"]),
    ("Official winner/ATS/total grading", ["tests.test_game_official_results"]),
    ("Player prop archive grading", ["tests.test_pregame_archive_grading"]),
    ("Player result grading", ["tests.test_player_result_audit"]),
]
for label, modules in groups:
    run(label, [sys.executable, "-m", "unittest", "-v", *modules])

run("Python compile check", [sys.executable, "-m", "compileall", "-q", "live", "scripts", "tests", "tools"])
for path in sorted(ROOT.glob("*.js")):
    run("JS syntax: " + path.name, ["node", "--check", str(path)])

invalid = []
empty = []
count = 0
for path in sorted((ROOT / "data").glob("*.json")):
    count += 1
    if path.stat().st_size == 0:
        empty.append(path.name)
        continue
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        invalid.append(f"{path.name}: {exc}")
record("Published JSON integrity", "FAIL" if invalid else "PASS", f"{count} checked; invalid: " + (", ".join(invalid) if invalid else "none"))
if empty:
    record("Empty JSON feeds", "WARN", ", ".join(empty))

for filename in ["game-official-pregame-locks.json", "dk-pregame-lines.json", "player-history.json", "game-pregame-observations.json"]:
    path = ROOT / "data" / filename
    if not path.exists():
        record("Archive: " + filename, "WARN", "File not present; verify expected output path")
        continue
    if path.stat().st_size == 0:
        record("Archive: " + filename, "WARN", "Empty; no verified frozen records")
        continue
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        record("Archive: " + filename, "PASS", "Valid JSON; record coverage and kickoff timestamps require separate verification")
    except (ValueError, UnicodeError) as exc:
        record("Archive: " + filename, "FAIL", str(exc))

report = [
    "# FOURTHDOWN Full System Audit",
    f"Generated: {datetime.now(timezone.utc).isoformat()}",
    "",
    "Read-only offline checks. PASS means these checks passed, not that every game has a frozen pregame snapshot.",
    "",
    "| Check | Result | Details |",
    "|---|---|---|",
]
report.extend(f"| {name} | {status} | {detail} |" for name, status, detail in results)
report.extend(["", f"**Totals:** {sum(s == 'PASS' for _, s, _ in results)} passed, {sum(s == 'FAIL' for _, s, _ in results)} failed, {sum(s == 'WARN' for _, s, _ in results)} warnings."])
report_text = "\n".join(report) + "\n"
Path("full-system-audit-report.md").write_text(report_text, encoding="utf-8")
summary = os.environ.get("GITHUB_STEP_SUMMARY")
if summary:
    with open(summary, "a", encoding="utf-8") as handle:
        handle.write(report_text)
print(report_text)
sys.exit(1 if any(status == "FAIL" for _, status, _ in results) else 0)
