"""Conservative, configurable weather scenario template.

Scenario-only until evaluated against frozen pregame holdouts. No automatic
production activation. All values are hypotheses, not measured NFL effects.
"""
from dataclasses import dataclass,asdict
from typing import Optional

@dataclass(frozen=True)
class WeatherScenario:
    total_points_delta:float=0
    pass_yards_pct:float=0
    pass_attempts_pct:float=0
    receptions_pct:float=0
    rush_attempts_pct:float=0
    rush_efficiency_pct:float=0
    reasons:tuple=()

def scenario(wind_mph:Optional[float],temp_f:Optional[float],heavy_precip:bool=False,roof:str="outdoor"):
    if roof.lower() in ("closed","dome"):
        return WeatherScenario()
    if roof.lower() not in ("outdoor","open") or wind_mph is None or temp_f is None:
        return None
    if not 0<=wind_mph<=150 or not -100<=temp_f<=140:
        return None
    p=pa=rec=ra=eff=pts=0.0
    reasons=[]
    if wind_mph>=25:
        pts-=5;p-=.12;pa-=.04;rec-=.08;ra+=.06;eff-=.02;reasons.append("wind_25_plus")
    elif wind_mph>=18:
        pts-=3;p-=.07;pa-=.02;rec-=.05;ra+=.03;eff-=.01;reasons.append("wind_18_24")
    elif wind_mph>=12:
        pts-=1;p-=.03;rec-=.02;ra+=.01;reasons.append("wind_12_17")
    if temp_f<=20:
        pts-=1;p-=.02;ra+=.01;reasons.append("extreme_cold")
    if heavy_precip:
        pts-=2;p-=.05;rec-=.03;ra+=.03;eff-=.03;reasons.append("heavy_precipitation")
    return WeatherScenario(max(-7,pts),max(-.18,p),max(-.08,pa),
        max(-.12,rec),min(.08,ra),max(-.06,eff),tuple(reasons))

def adjusted_projection(market,baseline,weather):
    if weather is None or baseline is None:return None
    if baseline<0:raise ValueError("Negative baseline")
    factors={
        "passing_yards":weather.pass_yards_pct,
        "receiving_yards":weather.pass_yards_pct,
        "pass_attempts":weather.pass_attempts_pct,
        "receptions":weather.receptions_pct,
        "rush_attempts":weather.rush_attempts_pct,
        "rushing_yards":(1+weather.rush_attempts_pct)*(1+weather.rush_efficiency_pct)-1,
    }
    if market=="game_total":return max(0,baseline+weather.total_points_delta)
    if market in ("home_score","away_score"):
        return max(0,baseline+weather.total_points_delta/2)
    if market not in factors:return baseline
    return max(0,baseline*(1+factors[market]))
