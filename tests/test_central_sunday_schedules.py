import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def events(name):
    text = (ROOT / '.github/workflows' / name).read_text()
    return re.findall(r"- cron: '([^']+)'\s*\n\s*timezone: (\S+)", text)


class SundayCentralScheduleTests(unittest.TestCase):
    def test_primary_presets_use_central_in_both_seasons(self):
        self.assertEqual(events('sunday-preset-game-day-refresh.yml'), [
            ('0 8 * * 0', 'America/Chicago'), ('0 11 * * 0', 'America/Chicago'),
            ('30 14 * * 0', 'America/Chicago'), ('45 18 * * 0', 'America/Chicago')])
        source = (ROOT / '.github/workflows/sunday-preset-game-day-refresh.yml').read_text()
        for expr, _ in events('sunday-preset-game-day-refresh.yml'):
            self.assertIn('"' + expr + '"', source)
        self.assertIn('ZoneInfo("America/Chicago")', source)

    def test_recovery_ticks_cover_each_slot_and_following_hour(self):
        self.assertEqual(events('sunday-preset-backstop.yml'), [
            ('7,37 8,11,14,15,18,19 * * 0', 'America/Chicago')])


if __name__ == '__main__':
    unittest.main()
