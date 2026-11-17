import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/daily-dk-player-props.yml"


class DailyDraftKingsRefreshTests(unittest.TestCase):
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
