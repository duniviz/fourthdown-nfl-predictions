"""Portable game-score ML shadow inference; invalid or stale data falls back."""
import json, math
from pathlib import Path
FAMILY='game-score-ridge-v1'
MARKETS=('game_margin_home','game_total')

def load_runtime(path=Path('data/game-ml-runtime.json')):
    try:
        d=json.loads(path.read_text())
        return d if d.get('family')==FAMILY and isinstance(d.get('models'),dict) else {}
    except (OSError,ValueError,TypeError,AttributeError): return {}

def game_features(game):
    try:
        analysis=game['analysis'];result=[]
        for side in ('home','away'):
            rows=analysis[side]['recent_form']['results']
            if len(rows)<3:return None
            rows=rows[-5:]
            result.extend([sum(float(r['points_for']) for r in rows)/len(rows),
                           sum(float(r['points_against']) for r in rows)/len(rows)])
        result.append(int(game['week']))
        return result if all(math.isfinite(x) for x in result) else None
    except (KeyError,TypeError,ValueError,ZeroDivisionError):return None

def apply(game,runtime):
    """Apply active candidates and preserve the exact matched shadow pair."""
    if runtime.get('family')!=FAMILY:return game
    features=game_features(game)
    if features is None:return game
    try: season=int(game['season']);week=int(game['week'])
    except (KeyError,TypeError,ValueError):return game
    baseline={'game_margin_home':float(game['projected_margin_home']),'game_total':float(game['projected_total'])}
    if not all(math.isfinite(v) for v in baseline.values()) or baseline['game_total']<0:return game
    output=dict(baseline);shadow={}
    for market in MARKETS:
        try:
            m=runtime['models'][market];year=int(m['trained_season']);w=int(m['trained_week'])
            fresh=(year==season and w<week<=w+2) or (year==season-1 and w>=17 and week<=2)
            if not fresh:continue
            coef=[float(x) for x in m['coefficients']];intercept=float(m['intercept'])
            if len(coef)!=5 or not all(math.isfinite(x) for x in [intercept,*coef]):continue
            raw=intercept+sum(a*b for a,b in zip(coef,features));base=baseline[market]
            cap=3.0 if market=='game_margin_home' else 4.0
            candidate=round(max(base-cap,min(base+cap,raw)),2)
            # Preserve physically possible scores without changing the other market.
            if market=='game_margin_home':candidate=max(-baseline['game_total'],min(baseline['game_total'],candidate))
            else:candidate=max(abs(baseline['game_margin_home']),candidate)
            active=runtime.get('decisions',{}).get(market,{}).get('active') is True
            shadow[market]={'baseline':base,'candidate':candidate,'active':active,
                            'trained_season':year,'trained_week':w}
            if active:output[market]=candidate
        except (KeyError,ValueError,TypeError,OverflowError):continue
    if not shadow:return game
    # If both markets are active, keep final scores nonnegative.
    if abs(output['game_margin_home'])>output['game_total']:
        output=dict(baseline)
        for pair in shadow.values():pair['active']=False
    game['game_ml_shadow']={'family':FAMILY,'markets':shadow}
    if not any(pair['active'] for pair in shadow.values()):return game
    margin,total=output['game_margin_home'],output['game_total']
    game.update(projected_margin_home=round(margin,2),projected_total=round(total,2),
                projected_home_score=round((total+margin)/2,1),projected_away_score=round((total-margin)/2,1),
                predicted_winner=game['home'] if margin>0 else game['away'])
    return game
