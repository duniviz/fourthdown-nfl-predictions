"""Match fresh ESPN scoreboard kickoff times to unique NFL scheduled games."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone


def stamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def team(name):
    value = str(name or '').upper().strip()
    return {'LAR': 'LA', 'WSH': 'WAS', 'JAC': 'JAX'}.get(value, value)


def scoreboard_kickoffs(schedules, feed, now):
    if not isinstance(feed, dict) or not isinstance(feed.get('events'), list):
        return {}
    updated = stamp(feed.get('updated_at_utc'))
    if not updated or not timedelta(0) <= now - updated <= timedelta(hours=12):
        return {}
    scheduled = defaultdict(list)
    for g in schedules:
        try:
            if g.get('game_type') != 'REG' or not g.get('game_id'):
                continue
            key = (int(g['season']), int(g['week']), team(g['home_team']), team(g['away_team']))
            if not key[2] or not key[3] or key[2] == key[3]:
                continue
            scheduled[key].append(g)
        except (KeyError, ValueError, TypeError):
            continue
    events = defaultdict(list)
    for e in feed['events']:
        try:
            if e['season']['type'] != 2 or len(e['competitions']) != 1:
                continue
            comp = e['competitions'][0]
            if comp.get('timeValid') is False or len(comp['competitors']) != 2:
                continue
            sides = {p['homeAway']: team(p['team']['abbreviation']) for p in comp['competitors']}
            key = (int(e['season']['year']), int(e['week']['number']), sides['home'], sides['away'])
            when, competition_when = stamp(e.get('date')), stamp(comp.get('date'))
            if not when or when != competition_when:
                continue
            events[key].append(when)
        except (KeyError, TypeError, ValueError):
            continue
    result = {}
    for key, games in scheduled.items():
        if len(games) != 1 or len(events.get(key, [])) != 1:
            continue
        g, when = games[0], events[key][0]
        try:
            # A week-scale bound prevents mismatching distant or malformed dates.
            reference = datetime.fromisoformat(str(g['gameday'])).replace(tzinfo=timezone.utc)
            if abs(when - reference) > timedelta(days=7):
                continue
        except (KeyError, TypeError, ValueError):
            continue
        result[str(g['game_id'])] = when
    return result
