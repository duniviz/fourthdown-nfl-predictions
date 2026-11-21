"""Build strictly prior-week coaching and defensive-efficiency research features.

Coach attribution is a last-known head-coach proxy, not a coordinator or an
assertion that the target game's staff was known before kickoff.
"""
from collections import defaultdict
from math import isfinite


def val(x):
    try:
        f = float(x)
        return f if isfinite(f) else None
    except (ValueError, TypeError):
        return None


def build(games, plays):
    scheduled = {}
    weeks = defaultdict(list)
    for g in games:
        try:
            year, week = int(g['season']), int(g['week'])
            gid = str(g['game_id'])
            if g.get('game_type') != 'REG' or val(g.get('home_score')) is None or val(g.get('away_score')) is None:
                continue
            if not g.get('home_team') or not g.get('away_team'):
                continue
            scheduled[gid] = g
            weeks[(year, week)].append(g)
        except (KeyError, ValueError, TypeError):
            continue
    # Sums and counts, keyed by exact game/team to avoid double counting.
    stats = defaultdict(lambda: defaultdict(float))
    for p in plays:
        gid = str(p.get('game_id') or '')
        game = scheduled.get(gid)
        kind = p.get('play_type')
        off, defense = p.get('posteam'), p.get('defteam')
        if not game or kind not in ('run', 'pass') or {off, defense} != {game['home_team'], game['away_team']}:
            continue
        o, d = stats[(gid, off)], stats[(gid, defense)]
        diff = val(p.get('score_differential'))
        if diff is not None and abs(diff) <= 8:
            o['neutral_n'] += 1
            o['neutral_pass'] += kind == 'pass'
        if diff is not None and diff < -7:
            o['trailing_n'] += 1
            o['trailing_pass'] += kind == 'pass'
        yards = val(p.get('yards_gained'))
        if yards is not None:
            d[kind + '_n'] += 1
            d[kind + '_yards'] += yards
    team_history = defaultdict(list)
    coach_history = defaultdict(list)
    last_coach = {}
    output = {}

    def totals(rows, prefix):
        n = sum(r.get(prefix + '_n', 0) for r in rows)
        numerator = sum(r.get(prefix + ('_pass' if prefix in ('neutral', 'trailing') else '_yards'), 0) for r in rows)
        return numerator / n if n else None

    for key in sorted(weeks):
        pending = []
        for g in weeks[key]:
            gid = str(g['game_id'])
            sides = []
            for side in ('home', 'away'):
                team = g[side + '_team']
                past = team_history[(key[0], team)][-5:]
                coach = last_coach.get(team)
                coach_past = coach_history.get(coach, [])[-16:] if coach else []
                if len(past) < 3 or len(coach_past) < 3:
                    sides.append(None)
                else:
                    sides.append({'neutral_pass': totals(coach_past, 'neutral'),
                                  'trailing_pass': totals(coach_past, 'trailing'),
                                  'allowed_per_run': totals(past, 'run'),
                                  'allowed_per_pass_play': totals(past, 'pass')})
                observed_coach = g.get(side + '_coach')
                pending.append((key[0], team, observed_coach, dict(stats[(gid, team)])))
            if all(sides) and all(v is not None for side in sides for v in side.values()):
                h, a = sides
                output[gid] = {'coach': [h['neutral_pass'], a['neutral_pass'], h['trailing_pass'], a['trailing_pass']],
                               'defense': [h['allowed_per_run'], a['allowed_per_run'], h['allowed_per_pass_play'], a['allowed_per_pass_play']]}
        # No game of this week is visible to any other game in the same week.
        for year, team, coach, s in pending:
            if s.get('neutral_n'):
                team_history[(year, team)].append(s)
                if coach:
                    coach_history[coach].append(s)
                    last_coach[team] = coach
    return output
