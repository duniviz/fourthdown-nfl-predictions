"""Fail-closed inference for the weekly paired-shadow player ML trial."""
import json
import math
from pathlib import Path

MODEL_FAMILY = 'paired-ridge-v1'
MARKETS = ('passing_yards', 'rushing_yards', 'receiving_yards')


def load_runtime(path=Path('data/player-ml-runtime.json')):
    try:
        value = json.loads(path.read_text())
        if value.get('family') != MODEL_FAMILY or not isinstance(value.get('models'), dict):
            return {}
        return value
    except (OSError, ValueError, AttributeError, TypeError):
        return {}


def forecast(runtime, market, base, season, week):
    """Return an exact live-input candidate; never use same-week training."""
    try:
        if runtime.get('family') != MODEL_FAMILY or market not in MARKETS:
            return None
        m = runtime['models'][market]
        year, week = int(season), int(week)
        trained_year, trained_week = int(m['trained_season']), int(m['trained_week'])
        if (year, week) <= (trained_year, trained_week):
            return None
        # Stale or missed weekly runs cannot keep an old model active indefinitely.
        fresh = (year == trained_year and week <= trained_week + 2) or (year == trained_year + 1 and week <= 2 and trained_week >= 17)
        if not fresh:
            return None
        base=float(base)
        coef=[float(x) for x in m['coefficients']]; intercept=float(m['intercept'])
        if len(coef)!=2 or not all(math.isfinite(x) for x in [base,intercept,*coef]) or base<0:
            return None
        candidate=max(0.0, intercept+coef[0]*base+coef[1]*week)
        # Constrain exposure to a 25% change while the model is evaluated.
        candidate=min(base*1.25,max(base*.75,candidate))
        return round(candidate,1)
    except (KeyError,TypeError,ValueError,OverflowError):
        return None


def use_projection(runtime, market, base, season, week):
    candidate=forecast(runtime,market,base,season,week)
    if candidate is None: return base, None
    active=runtime.get('decisions',{}).get(market,{}).get('active') is True
    return (candidate if active else base), {'family':MODEL_FAMILY,'baseline':round(float(base),1),
            'candidate':candidate,'active':active,
            'trained_season':runtime['models'][market]['trained_season'],
            'trained_week':runtime['models'][market]['trained_week']}
