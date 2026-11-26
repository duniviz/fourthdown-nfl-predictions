"""UTC capture and forecast schedules, checked against America/Chicago kickoffs."""
import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from live.pregame_capture_guard import due_lock, due_refresh, lock_wait_seconds

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/capture-game-pregame.yml"
GRADING = ROOT / ".github/workflows/nightly-game-grading.yml"
FORECAST = ROOT / ".github/workflows/publish-v2.yml"
WEEKLY_ML = ROOT / ".github/workflows/fourthdown-unified-weekly-ml.yml"
CT = ZoneInfo("America/Chicago")
UTC = timezone.utc

# python weekday(): Monday=0 ... Sunday=6
THU, SAT, SUN, MON = 3, 5, 6, 0


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


def cron_exprs(text):
    return re.findall(r"cron:\s*'([^']+)'", text)


def cron_matches(expr, utc_dt):
    minute, hour, dom, month, dow = expr.split()
    if utc_dt.minute not in field(minute, 0, 59):
        return False
    if utc_dt.hour not in field(hour, 0, 23):
        return False
    if utc_dt.month not in field(month, 1, 12):
        return False
    dom_ok = utc_dt.day in field(dom, 1, 31)
    cron_dow = (utc_dt.weekday() + 1) % 7
    dow_ok = cron_dow in field(dow, 0, 6)
    if dom == "*" and dow == "*":
        return True
    if dom == "*":
        return dow_ok
    if dow == "*":
        return dom_ok
    # GitHub runs the job when either calendar field matches.
    return dom_ok or dow_ok


def slot_exprs(exprs):
    """Drop always-on nets so coverage has to come from the game ticks."""
    kept = []
    for expr in exprs:
        _minute, _hour, dom, month, dow = expr.split()
        if dom == "*" and month == "*" and dow == "*":
            continue
        kept.append(expr)
    return kept


def lead_minutes(exprs, kickoff):
    found = set()
    for delta in range(0, 181):
        instant = (kickoff - timedelta(minutes=delta)).astimezone(UTC).replace(second=0, microsecond=0)
        if any(cron_matches(expr, instant) for expr in exprs):
            found.add(delta)
    return found


def at_ct(year, month, day, hour, minute):
    return datetime(year, month, day, hour, minute, tzinfo=CT)


def first_weekday(year, month, python_weekday):
    day = datetime(year, month, 1)
    while day.weekday() != python_weekday:
        day += timedelta(days=1)
    return day.day


def regular_kickoffs():
    """One CST date and one CDT date for each weekly slot, plus January."""
    slots = (
        (THU, 19, 15),
        (SAT, 8, 30),
        (SUN, 8, 30),
        (SUN, 12, 0),
        (SUN, 15, 5),
        (SUN, 15, 25),
        (SUN, 19, 20),
        (MON, 19, 15),
    )
    dates = []
    for year, month in ((2026, 10), (2026, 9), (2026, 12), (2027, 1)):
        for weekday, hour, minute in slots:
            day = first_weekday(year, month, weekday)
            dates.append(at_ct(year, month, day, hour, minute))
    return dates


HOLIDAY_KICKOFFS = (
    at_ct(2026, 11, 26, 12, 0),
    at_ct(2026, 11, 26, 15, 30),
    at_ct(2026, 11, 26, 19, 20),
    at_ct(2026, 11, 27, 14, 0),
    at_ct(2026, 12, 24, 19, 15),
    at_ct(2026, 12, 25, 12, 0),
    at_ct(2026, 12, 25, 15, 30),
    at_ct(2026, 12, 25, 19, 15),
    at_ct(2026, 12, 26, 15, 30),
    at_ct(2026, 12, 26, 19, 0),
    at_ct(2026, 12, 19, 16, 0),
    at_ct(2026, 12, 19, 19, 20),
)


class CaptureTimingTests(unittest.TestCase):
    def test_schedules_are_utc_and_do_not_or_the_calendar_fields(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        forecast = FORECAST.read_text(encoding="utf-8")
        self.assertNotIn("timezone:", source)
        self.assertNotIn("timezone:", forecast)
        self.assertNotIn("cron: '2,12,22,32,42,52 * * * *'", source)
        self.assertIn("cron: '22 0-5,13-23 * * *'", source)
        for expr in cron_exprs(source) + cron_exprs(forecast):
            minute, _hour, dom, _month, dow = expr.split()
            self.assertFalse(dom != "*" and dow != "*", msg=expr)
            self.assertNotIn(0, field(minute, 0, 59), msg=expr)
            self.assertNotIn(expr.split()[0], {"0", "*/5", "*/10"})

    def test_slot_ticks_land_in_each_kickoff_window(self):
        capture = slot_exprs(cron_exprs(WORKFLOW.read_text(encoding="utf-8")))
        forecast = slot_exprs(cron_exprs(FORECAST.read_text(encoding="utf-8")))
        for kickoff in list(regular_kickoffs()) + list(HOLIDAY_KICKOFFS):
            label = kickoff.strftime("%a %Y-%m-%d %H:%M %Z")
            leads = lead_minutes(capture, kickoff)
            lock = sorted(value for value in leads if 30 <= value <= 45)
            late = sorted(value for value in leads if 5 <= value <= 29)
            self.assertGreaterEqual(len(lock), 3, msg=f"{label} lock={lock}")
            self.assertGreaterEqual(len(late), 2, msg=f"{label} late={late}")
            self.assertLessEqual(lock[-1] - lock[0], 15, msg=lock)
            fresh = sorted(value for value in lead_minutes(forecast, kickoff) if 80 <= value <= 120)
            self.assertGreaterEqual(len(fresh), 3, msg=f"{label} forecast={fresh}")

    def test_hourly_fallback_covers_8am_through_11pm_ct(self):
        expr = "22 0-5,13-23 * * *"
        self.assertIn(expr, cron_exprs(WORKFLOW.read_text(encoding="utf-8")))
        for year, month, day in ((2026, 9, 13), (2026, 10, 4), (2026, 12, 6), (2027, 1, 10)):
            for hour in range(8, 24):
                local = at_ct(year, month, day, hour, 22)
                utc = local.astimezone(UTC)
                self.assertTrue(cron_matches(expr, utc), msg=local.isoformat())
            # 6:22 AM CT is before the fallback in both CST and CDT.
            early = at_ct(year, month, day, 6, 22).astimezone(UTC)
            self.assertFalse(cron_matches(expr, early), msg=early.isoformat())

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
        self.assertEqual(lock_wait_seconds(games,kickoff-timedelta(minutes=40)),600)
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

    def test_tuesday_forecast_follows_successful_evaluation(self):
        source = FORECAST.read_text(encoding="utf-8")
        ml = WEEKLY_ML.read_text(encoding="utf-8")
        self.assertIn("workflows: [Daily DraftKings player prop refresh, FOURTHDOWN unified weekly ML cycle, Publish ESPN scoreboard backup]", source)
        self.assertIn('github.event.workflow_run.name }}" == "FOURTHDOWN unified weekly ML cycle', source)
        self.assertLess(source.index('github.event.workflow_run.conclusion'), source.index('github.event.workflow_run.name'))
        self.assertIn("workflows: [Tuesday pre-forecast evaluation]", ml)
        self.assertNotIn("45 16 * * 3", ml)

    def test_nightly_grade_accepts_a_delayed_cron(self):
        source = GRADING.read_text(encoding="utf-8")
        self.assertIn("python -m live.game_official_results --due --event", source)
        self.assertNotIn('date +%H)" == "23"', source)


if __name__ == "__main__":
    unittest.main()
