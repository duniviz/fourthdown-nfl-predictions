import unittest
import datetime as dt
import json
import os
import subprocess
import tempfile
import textwrap
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/daily-dk-player-props.yml"


class DailyDraftKingsRefreshTests(unittest.TestCase):
    def run_schedule_guard(self, games, schedule):
        source = WORKFLOW.read_text(encoding="utf-8")
        start = source.index("        run: |\n", source.index("- name: Check scheduled refresh window"))
        end = source.index("      - name:", start)
        script = textwrap.dedent(source[start + len("        run: |\n"):end])
        script = script.replace("${{ github.event_name }}", "schedule")
        script = script.replace("${{ github.event.schedule }}", schedule)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "data/live-v2.json").write_text(json.dumps({"games": games}))
            output = root / "output"
            env = dict(os.environ, GITHUB_OUTPUT=str(output))
            result = subprocess.run(["bash", "-e", "-c", script], cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return dict(line.split("=", 1) for line in output.read_text().splitlines())

    def test_daily_and_retry_ticks_run_only_on_verified_non_game_days(self):
        central = ZoneInfo("America/Chicago")
        now = dt.datetime.now(central)
        today = now.replace(hour=12, minute=0, second=0, microsecond=0)
        other_day = today + dt.timedelta(days=1)
        for cron in ("40 16 * * *", "10,40 17 * * *"):
            with self.subTest(cron=cron):
                self.assertEqual(self.run_schedule_guard([{"kickoff_utc": other_day.isoformat()}], cron)["run"], "true")
                self.assertEqual(self.run_schedule_guard([{"kickoff_utc": today.isoformat()}], cron)["run"], "false")
                self.assertEqual(self.run_schedule_guard([], cron)["run"], "false")

    def test_daily_job_refreshes_game_markets_but_hourly_prop_ticks_do_not(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        start = source.index("- name: Refresh upcoming DK game spreads")
        end = source.index("- name: Refresh DK player props", start)
        step = source[start:end]
        self.assertIn("python -m live.dk_game_refresh", step)
        self.assertIn("github.event.schedule != '37 * * * 1,4,5,6'", step)
        self.assertIn("continue-on-error: true", step)
        self.assertIn("PARLAY_API_KEY:", step)
        self.assertIn("branches: [main]", source)
        self.assertIn(".github/workflows/daily-dk-player-props.yml", source)

    def test_game_line_snapshot_and_history_are_published(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("data/dk-game-odds.json", source)
        self.assertIn("data/dk-game-line-history.json", source)
        self.assertIn("git add -f data/dk-odds.json data/dk-opening-odds.json data/dk-game-odds.json data/dk-game-line-history.json", source)


if __name__ == "__main__":
    unittest.main()
