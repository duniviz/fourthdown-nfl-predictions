"""Hold one GitHub Actions run until a kickoff window, then re-dispatch if it is still far away.

GitHub delivers only a handful of scheduled runs per day and drops most
five-minute ticks. A run that does start sleeps until the existing window
(forecast 80–150 minutes, aimed at T-115 so the stamp stays inside 2 hours;
capture T-45..T-30) or, past a few hours, dispatches itself and exits.
"""
import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from live.game_pregame_observations import dt
from live.pregame_capture_guard import cycle_due
from scripts.check_pregame_forecast_window import FORECAST_FRESH, MAX_MINUTES, MIN_MINUTES
from scripts.stale_forecast_recovery import recovery_due

CENTRAL = ZoneInfo("America/Chicago")
FORECAST_TARGET_MINUTES = 115
CAPTURE_OPEN_MINUTES = 45
CAPTURE_TARGET_MINUTES = 42
GROUP_GAP = timedelta(minutes=40)
MAX_SLEEP_SECONDS = 320 * 60
HORIZON_SECONDS = 14 * 3600
DAILY_SCHEDULES = {"17 22 * * *", "17 23 * * *", "30 0,1,2 * * 2"}
WORKFLOWS = {"forecast": "publish-v2.yml", "capture": "capture-game-pregame.yml"}


class Decision:
    def __init__(self, action, seconds=0, reason=""):
        self.action = action
        self.seconds = max(0, int(seconds))
        self.reason = reason

    def __repr__(self):
        return f"Decision({self.action!r}, {self.seconds}, {self.reason!r})"


def kickoffs_of(games):
    found = []
    for game in games or []:
        if not isinstance(game, dict):
            continue
        kickoff = dt(game.get("kickoff_utc"))
        if kickoff:
            found.append(kickoff)
    return sorted(set(found))


def covered(kickoff, generated):
    return bool(generated and kickoff - FORECAST_FRESH <= generated < kickoff)


def forecast_plan(games, generated, now):
    future = [kickoff for kickoff in kickoffs_of(games) if kickoff > now and not covered(kickoff, generated)]
    if not future:
        return Decision("skip", 0, "no kickoff still needs a forecast")
    for index, earliest in enumerate(future):
        close = earliest - timedelta(minutes=MIN_MINUTES)
        open_at = earliest - timedelta(minutes=MAX_MINUTES)
        if now > close:
            continue
        if now < open_at and (open_at - now).total_seconds() > HORIZON_SECONDS:
            return Decision("skip", 0, "next forecast window is outside the horizon")
        target = earliest - timedelta(minutes=FORECAST_TARGET_MINUTES)
        grouped = [earliest]
        for later in future[index + 1:]:
            if later - earliest > GROUP_GAP:
                break
            grouped.append(later)
            preferred = later - timedelta(minutes=FORECAST_TARGET_MINUTES)
            if preferred <= close:
                target = max(target, preferred)
        if target > close:
            target = close
        if target < open_at:
            target = open_at
        # An instant stamp still has to sit inside 2 hours of the later grouped kickoff.
        earliest_safe = grouped[-1] - FORECAST_FRESH
        if target < earliest_safe <= close:
            target = earliest_safe
        if now >= target:
            return Decision("run", 0, "inside the 80–150 minute window")
        delay = (target - now).total_seconds()
        if delay <= MAX_SLEEP_SECONDS:
            return Decision("sleep", delay, "waiting until about T-115")
        return Decision("chain", MAX_SLEEP_SECONDS, "forecast window is further out")
    return Decision("skip", 0, "forecast windows already closed")


def capture_plan(games, now, later_only=False):
    future = [kickoff for kickoff in kickoffs_of(games) if kickoff > now]
    if later_only:
        # The run that just finished waited through T-30, so drop kickoffs already inside that lock.
        future = [kickoff for kickoff in future if (kickoff - now) > timedelta(minutes=30)]
    if not future:
        return Decision("skip", 0, "no upcoming capture")
    earliest = future[0]
    remaining = (earliest - now).total_seconds() / 60
    if remaining <= CAPTURE_OPEN_MINUTES:
        return Decision("run", 0, "inside T-45 to kickoff")
    if (earliest - now).total_seconds() > HORIZON_SECONDS:
        return Decision("skip", 0, "next capture is outside the horizon")
    target = earliest - timedelta(minutes=CAPTURE_TARGET_MINUTES)
    delay = (target - now).total_seconds()
    if delay <= MAX_SLEEP_SECONDS:
        return Decision("sleep", delay, "waiting until T-42")
    return Decision("chain", MAX_SLEEP_SECONDS, "capture window is further out")


def should_wait(event, arm):
    if event in ("schedule", "workflow_run"):
        return True
    return event == "workflow_dispatch" and arm


def gate(role, games, generated, now, event="schedule", schedule="", workflow_name="",
         conclusion="success", arm=False, later_only=False, manual_capture_due=False):
    if role == "forecast" and event == "workflow_run" and conclusion not in ("success", "", None):
        return Decision("skip", 0, "upstream workflow did not succeed")
    if not should_wait(event, arm):
        if role == "forecast":
            return Decision("run", 0, "immediate forecast")
        return Decision("run" if manual_capture_due else "skip", 0, "immediate capture check")
    if role == "forecast" and event == "workflow_run" and workflow_name == "FOURTHDOWN unified weekly ML cycle":
        return Decision("run", 0, "Tuesday ML cycle")
    if (role == "forecast" and event == "workflow_run"
            and workflow_name == "Daily DraftKings player prop refresh"
            and now.astimezone(CENTRAL).isoweekday() == 7):
        return Decision("run", 0, "Sunday DraftKings refresh")
    if role == "forecast" and event == "schedule" and schedule in DAILY_SCHEDULES:
        return Decision("run", 0, "daily schedule")
    if role == "forecast":
        return forecast_plan(games, generated, now)
    return capture_plan(games, now, later_only=later_only)


def load_slate():
    path = Path("data/live-v2.json")
    data = json.loads(path.read_text()) if path.exists() else {}
    games = data.get("games", []) if isinstance(data, dict) else []
    generated = dt(data.get("generated_at_utc")) if isinstance(data, dict) else None
    return data if isinstance(data, dict) else {}, games, generated


def load_done():
    path = Path("data/dk-slate-refreshes.json")
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text()).get("slates", []))
    except (OSError, ValueError, TypeError):
        return set()


def emit(name, enabled):
    print(f"{name}={'true' if enabled else 'false'}", flush=True)
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={'true' if enabled else 'false'}\n")


def refresh_checkout():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    subprocess.run(["git", "pull", "--ff-only", "origin", "main"], check=False)


def sleep_until(seconds):
    remaining = int(seconds)
    while remaining > 0:
        chunk = min(remaining, 600)
        time.sleep(chunk)
        remaining -= chunk
        if remaining:
            print(f"Still waiting, {remaining}s left", flush=True)


def dispatch(role):
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        raise RuntimeError("Missing GH_TOKEN or GITHUB_REPOSITORY; cannot arm the next run")
    workflow = WORKFLOWS[role]
    body = json.dumps({"ref": "main", "inputs": {"wait_for_window": True}}).encode()
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/dispatches",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "fourthdown-pregame-window",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        print(f"Dispatched {workflow} to keep waiting ({response.status})", flush=True)


def decide_from_env(role, follow_up):
    event = os.environ.get("EVENT_NAME", "schedule")
    schedule = os.environ.get("EVENT_SCHEDULE", "")
    workflow_name = os.environ.get("WORKFLOW_NAME", "")
    conclusion = os.environ.get("WORKFLOW_CONCLUSION", "success")
    arm = os.environ.get("ARM_WAIT", "") == "true"
    slate, games, generated = load_slate()
    now = datetime.now(timezone.utc)
    if follow_up:
        if role == "forecast":
            return forecast_plan(games, generated, now), slate, games, generated
        return capture_plan(games, now, later_only=True), slate, games, generated
    manual_due = cycle_due(games, load_done(), now) if role == "capture" else False
    return gate(role, games, generated, now, event, schedule, workflow_name, conclusion, arm,
                manual_capture_due=manual_due), slate, games, generated


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=("forecast", "capture"), required=True)
    parser.add_argument("--follow-up", action="store_true")
    args = parser.parse_args()
    output = "run" if args.role == "forecast" else "due"
    if args.follow_up:
        decision, _, _, _ = decide_from_env(args.role, True)
        print(f"follow-up {decision}", flush=True)
        # A capture can still need the next kickoff immediately. A forecast follow-up
        # only chains forward; repeating "run" would republish the kickoff just saved.
        arm_next = decision.action in ("sleep", "chain", "run") if args.role == "capture" else decision.action in ("sleep", "chain")
        if arm_next:
            try:
                dispatch(args.role)
            except (OSError, urllib.error.URLError, RuntimeError) as exc:
                print(f"::warning::Could not arm the next window ({exc})")
        else:
            print("No later kickoff window to arm")
        return 0
    for _ in range(4):
        decision, slate, games, generated = decide_from_env(args.role, False)
        print(decision, flush=True)
        if decision.action in ("sleep", "chain") and decision.seconds <= 1:
            decision = Decision("run", 0, decision.reason)
        if decision.action == "run":
            emit(output, True)
            return 0
        if decision.action == "skip":
            event = os.environ.get("EVENT_NAME", "schedule")
            if args.role == "forecast" and event == "schedule" and recovery_due(slate, datetime.now(timezone.utc)):
                print("Stale forecast recovery is due")
                emit(output, True)
                return 0
            emit(output, False)
            return 0
        if decision.action == "sleep":
            sleep_until(decision.seconds)
            refresh_checkout()
            continue
        sleep_until(decision.seconds)
        try:
            dispatch(args.role)
        except (OSError, urllib.error.URLError, RuntimeError) as exc:
            print(f"::error::Could not continue the pregame arm ({exc})")
            emit(output, False)
            return 1
        emit(output, False)
        return 0
    emit(output, False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
