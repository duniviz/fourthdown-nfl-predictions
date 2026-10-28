"""Fail publication on malformed player research; absent odds remain permitted."""
import json
import math
from pathlib import Path

YARD_LIMITS={"passing_yards":750,"rushing_yards":350,"receiving_yards":350}
COUNT_LIMITS={"attempts":85,"completions":65,"carries":55,"receptions":30,"passing_tds":9,"rushing_tds":6,"receiving_tds":6,"interceptions":7}

def validate(players):
    if not isinstance(players,list) or not players:
        raise ValueError("Missing player forecasts")
    for p in players:
        stat=p.get("stat_key")
        value=p.get("projection")
        if not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError(f"Invalid projection: {p.get('player')} {stat}")
        cap=100 if stat=="anytime_td" else YARD_LIMITS.get(stat,COUNT_LIMITS.get(stat))
        if cap is None or not 0<=value<=cap:
            raise ValueError(f"Implausible projection: {p.get('player')} {stat} {value}")
        if stat=="anytime_td":
            probability=p.get("projection_probability")
            if not isinstance(probability,(int,float)) or not 0<=probability<=1 or abs(value-100*probability)>.11:
                raise ValueError("Anytime TD percent/probability mismatch")
        elif stat in YARD_LIMITS and p.get("opportunity_type") not in ("attempts","carries","targets"):
            raise ValueError(f"Yardage market missing valid opportunity unit: {stat}")
        if stat in YARD_LIMITS:
            volume=p.get("expected_opportunities")
            rate=p.get("expected_yards_per_opportunity")
            if volume is not None and (not isinstance(volume,(int,float)) or not math.isfinite(volume) or volume<0):
                raise ValueError(f"Invalid workload: {p.get('player')} {stat} {volume}")
            if rate is not None and (not isinstance(rate,(int,float)) or not math.isfinite(rate) or rate<0):
                raise ValueError(f"Invalid efficiency: {p.get('player')} {stat} {rate}")
            # These are intentionally loose physical sanity bounds, not target forecasts.
            max_volume={"passing_yards":75,"rushing_yards":50,"receiving_yards":35}[stat]
            max_rate={"passing_yards":20,"rushing_yards":15,"receiving_yards":30}[stat]
            if volume is not None and volume>max_volume:
                raise ValueError(f"Unrealistic player workload: {p.get('player')} {stat} {volume}")
            if rate is not None and rate>max_rate:
                raise ValueError(f"Unrealistic yards per opportunity: {p.get('player')} {stat} {rate}")
            share=p.get("role_share")
            if share is not None and (not isinstance(share,(int,float)) or not math.isfinite(share) or share<0 or share>1.05):
                raise ValueError(f"Invalid team opportunity share: {p.get('player')} {stat} {share}")

    return len(players)

def main():
    payload=json.loads(Path("data/player-research.json").read_text(encoding="utf-8"))
    count=validate(payload.get("players"))
    print(f"Validated {count} player forecasts; no sportsbook quote required")

if __name__=="__main__":
    main()
