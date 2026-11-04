"""Research-only live NFL yardage game-script challenger. No production imports.
Inputs must be pre-snapshot data; compare against observed final totals."""
from dataclasses import dataclass
from math import isfinite
@dataclass
class Snapshot:
    actual_yards: float
    pregame_yards: float
    elapsed_minutes: float
    score_diff: int  # player's team minus opponent
    market: str  # passing_yards, rushing_yards, receiving_yards
    pass_attempts: float | None = None
    team_pass_attempts: float | None = None
    team_rush_attempts: float | None = None
    player_rush_attempts: float | None = None
    player_targets: float | None = None

def baseline(s: Snapshot) -> float:
    if not 3 <= s.elapsed_minutes <= 60: return float("nan")
    rate = s.pregame_yards / 60
    observed = min(rate*1.6, max(rate*0.5, s.actual_yards/s.elapsed_minutes))
    trust = min(.65, s.elapsed_minutes/60*.85)
    return max(s.actual_yards, s.actual_yards+(60-s.elapsed_minutes)*(rate*(1-trust)+observed*trust))

def challenger(s: Snapshot, strength: float = 1.0) -> float:
    """Heuristic volume adjustments; NOT calibrated. Strength=0 approximates baseline."""
    base = baseline(s)
    if not isfinite(base): return base
    remaining = max(0, 60-s.elapsed_minutes)
    # Game script becomes more influential late; moderate early signals.
    late = .35+.65*(s.elapsed_minutes/60)
    margin = min(abs(s.score_diff), 28)/14
    if s.market == "passing_yards":
        direction = -1 if s.score_diff > 0 else 1
        factor = 1 + direction * min(.30, .12*margin)*late*strength
    elif s.market == "rushing_yards":
        direction = 1 if s.score_diff > 0 else -1
        factor = 1 + direction * min(.22, .10*margin)*late*strength
    elif s.market == "receiving_yards":
        direction = -1 if s.score_diff > 0 else 1
        factor = 1 + direction * min(.25, .10*margin)*late*strength
    else: raise ValueError("unsupported market")
    # Adjust ONLY yards yet to be gained, not yards already recorded.
    return max(s.actual_yards, s.actual_yards + (base-s.actual_yards)*factor)

def grade(snapshots):
    """Rows: (Snapshot, verified_final_yards). Returns comparable MAE/RMSE."""
    from math import sqrt
    out={}
    for label,fn in (("baseline",baseline),("game_script",challenger)):
        errors=[fn(s)-final for s,final in snapshots if isfinite(fn(s))]
        out[label]={"n":len(errors),"mae":sum(abs(e) for e in errors)/len(errors) if errors else None,
                    "rmse":sqrt(sum(e*e for e in errors)/len(errors)) if errors else None}
    return out

if __name__=="__main__":
    # Synthetic behavior checks, not historical backtest results.
    s=Snapshot(212,260.9,36.0667,21,"passing_yards")
    t=Snapshot(212,260.9,36.0667,-21,"passing_yards")
    assert challenger(s)<baseline(s)<challenger(t)
    assert challenger(s)>=s.actual_yards
    print("Synthetic directional tests passed; no accuracy claim.")
