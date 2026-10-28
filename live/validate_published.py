"""Reject stale/mismatched simulation data before publishing the dashboard."""
import json
import math
from pathlib import Path

def validate(player_data, sim_data):
    players=player_data.get("players",[])
    sims=sim_data.get("players",[])
    if not players or not sims:
        raise ValueError("Missing player projections or simulations")
    index={}
    for s in sims:
        key=(s.get("game_id"),s.get("player_id"),s.get("stat_key"))
        if key in index:
            raise ValueError(f"Duplicate simulated player market: {key}")
        index[key]=s
    for p in players:
        key=(p.get("game_id"),p.get("player_id"),p.get("stat_key"))
        s=index.get(key)
        if s is None:
            raise ValueError(f"Missing simulation for {key}")
        expected=float(p.get("projection",0))
        simulated=float(s.get("mean_projection",float("nan")))
        if not math.isfinite(simulated) or abs(expected-simulated)>0.11:
            raise ValueError(f"Simulation/model projection mismatch: {key}: {expected} vs {simulated}")
    return len(players)

if __name__=="__main__":
    p=json.loads(Path("data/player-research.json").read_text())
    s=json.loads(Path("data/simulations.json").read_text())
    print(f"Validated {validate(p,s)} model/simulation pairs")
