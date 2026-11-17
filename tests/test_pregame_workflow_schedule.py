"""Slot-shaped capture schedule with several ticks inside each kickoff window."""
import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from live.pregame_capture_guard import due_lock, due_refresh, lock_wait_seconds

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/capture-game-pregame.yml"
GRADING = ROOT / ".github/workflows/nightly-game-grading.yml"


def field(expr, lo, hi):
    if expr == "*":
        return set(range(lo, hi + 1))
    out = set()
    for part in expr.split(","):
        if "-" in part:
            start, end = part.split("-")
            out.update(range(int(start), int(end) + 1))
        else:
            out.add(int(part))
    return out


def cron_events(text):
    events = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.search(r"cron:\s*'([^']+)'", line)
        if not match:
            continue
        timezone_name = None
        for follow in lines[index + 1:index + 3]:
            zone = re.search(r"timezone:\s*(\S+)", follow)
            if zone:
                timezone_name = zone.group(1).strip('"')
                break
        events.append((match.group(1), timezone_name))
    return events


def minutes_on(events, day):
    hits = set()
    for expr, _zone in events:
        minute, hour, _dom, _month, dow = expr.split()
        if day not in field(dow, 0, 6):
            continue
        for hour_value in field(hour, 0, 23):
            for minute_value in field(minute, 0, 59):
                hits.add(hour_value * 60 + minute_value)
    return hits


class CaptureTimingTests(unittest.TestCase):
    def test_slot_ticks_land_in_each_kickoff_window(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        events = cron_events(source)
        self.assertGreaterEqual(len(events), 8)
        self.assertTrue(all(zone == "America/Chicago" for _expr, zone in events))
        self.assertNotIn("cron: '2,12,22,32,42,52 * * * *'", source)
        # Thursday, early Saturday/Sunday, Sunday noon, both late windows, SNF, MNF.
        slots = (
            (4, 19, 15),
            (6, 8, 30),
            (0, 8, 30),
            (0, 12, 0),
            (0, 15, 5),
            (0, 15, 25),
            (0, 19, 20),
            (1, 19, 15),
        )
        for day, hour, minute in slots:
            kickoff = hour * 60 + minute
            hits = sorted(value for value in minutes_on(events, day) if kickoff - 40 <= value <= kickoff - 5)
            self.assertGreaterEqual(len(hits), 3, msg=f"dow={day} {hour:02d}:{minute:02d} hits={hits}")
            gaps = [b - a for a, b in zip(hits, hits[1:])]
            self.assertTrue(all(gap <= 15 for gap in gaps), msg=hits)
        for expr, _zone in events:
            self.assertNotIn(",0,", f",{expr.split()[0]},")
            self.assertFalse(expr.split()[0] in {"0", "*/5", "*/10"})

    def test_writer_runs_only_when_a_window_is_due(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python -m live.pregame_capture_guard --mode cycle", source)
        self.assertIn("timeout-minutes: 45", source)
        self.assertLess(source.index("preflight:"), source.index("concurrency:"))
        self.assertIn("group: pregame-pipeline", source)
        self.assertIn("cancel-in-progress: false", source)

    def test_lock_only_inside_t30_window_before_kickoff(self):
        kickoff = datetime(2026, 11, 16, 1, 20, tzinfo=timezone.utc)
        games = [{"kickoff_utc": kickoff.isoformat()}]
        self.assertFalse(due_lock(games, kickoff-timedelta(minutes=31)))
        self.assertTrue(due_lock(games, kickoff-timedelta(minutes=30)))
        self.assertTrue(due_lock(games, kickoff-timedelta(minutes=3)))
        self.assertFalse(due_lock(games, kickoff))
        self.assertFalse(due_lock(games, kickoff+timedelta(minutes=1)))

    def test_wait_targets_t30_and_not_the_old_t15_boundary(self):
        kickoff=datetime(2026,11,16,1,20,tzinfo=timezone.utc)
        games=[{"kickoff_utc":kickoff.isoformat()}]
        self.assertEqual(lock_wait_seconds(games,kickoff-timedelta(minutes=40)),580)
        self.assertEqual(lock_wait_seconds(games,kickoff-timedelta(minutes=30)),0)

    def test_refresh_chain_finishes_before_observation_and_lock_save(self):
        source=(ROOT / "live/pregame_cycle.py").read_text(encoding="utf-8")
        refresh=source[source.index("def refresh("):source.index("def checkpoint(")]
        self.assertLess(refresh.index('run_primary("game_odds"'), refresh.index('run_primary("player_props"'))
        self.assertLess(refresh.index('run_primary("player_props"'), refresh.index('if backup_needed('))
        self.assertLess(refresh.index('if backup_needed('), refresh.index('line_history.main()'))
        checkpoint=source[source.index("def checkpoint("):source.index("def next_wake(")]
        self.assertLess(checkpoint.index("observations.main()"), checkpoint.index("locks.main()"))
        self.assertLess(checkpoint.index("locks.main()"), checkpoint.index('publish("Save pregame'))

    def test_paid_refresh_survives_a_late_tick(self):
        kickoff = datetime(2026, 11, 16, 1, 20, tzinfo=timezone.utc)
        games = [{"kickoff_utc": kickoff.isoformat()}]
        self.assertEqual(due_refresh(games, set(), kickoff-timedelta(minutes=45)), [kickoff])
        self.assertEqual(due_refresh(games, set(), kickoff-timedelta(minutes=30)), [kickoff])
        self.assertEqual(due_refresh(games, set(), kickoff-timedelta(minutes=10)), [kickoff])
        self.assertEqual(due_refresh(games, {kickoff.isoformat()}, kickoff-timedelta(minutes=30)), [])
        self.assertEqual(due_refresh(games, set(), kickoff-timedelta(minutes=4)), [])

    def test_nightly_grade_accepts_a_delayed_cron(self):
        source = GRADING.read_text(encoding="utf-8")
        self.assertIn("python -m live.game_official_results --due --event", source)
        self.assertNotIn('date +%H)" == "23"', source)


if __name__ == "__main__":
    unittest.main()
