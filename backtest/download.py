"""Download historical NFL schedules and PBP-derived team EPA via nflreadpy.

Requires: pip install nflreadpy polars
Run: python -m backtest.download
Writes CSV under data/ (gitignored). No future weeks enter historical features.
"""
import csv
from pathlib import Path

YEARS = list(range(2021, 2026))

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def main():
    import nflreadpy as nfl
    import polars as pl
    target = Path("data")
    schedules = nfl.load_schedules(YEARS)
    required = ["season", "week", "game_id", "home_team", "away_team", "home_score", "away_score", "game_type"]
    optional = [x for x in ["spread_line", "total_line"] if x in schedules.columns]
    missing = set(required) - set(schedules.columns)
    if missing: raise ValueError(f"Schedules missing columns: {sorted(missing)}")
    write_csv(target / "schedules.csv", schedules.select(required + optional).to_dicts(), required + optional)
    rows = []
    for season in YEARS:
        pbp = nfl.load_pbp([season])
        needed = {"season", "week", "game_id", "posteam", "defteam", "epa", "play_type"}
        if needed - set(pbp.columns):
            raise ValueError(f"PBP missing columns: {sorted(needed-set(pbp.columns))}")
        # Exclude special teams and no-play records; per-game EPA avoids
        # incorrectly weighting weeks by number of plays.
        base = pbp.filter(
            pl.col("play_type").is_in(["pass", "run"])
            & pl.col("epa").is_not_null()
            & pl.col("posteam").is_not_null()
            & pl.col("defteam").is_not_null()
        )
        offense = base.group_by(["season", "week", "game_id", "posteam"]).agg(pl.col("epa").mean().alias("offense_epa")).rename({"posteam":"team"})
        defense = base.group_by(["season", "week", "game_id", "defteam"]).agg(pl.col("epa").mean().alias("defense_epa")).rename({"defteam":"team"})
        merged = offense.join(defense, on=["season", "week", "game_id", "team"], how="inner")
        rows.extend(merged.select(["season", "week", "team", "offense_epa", "defense_epa"]).to_dicts())
    write_csv(target / "team_epa.csv", rows, ["season", "week", "team", "offense_epa", "defense_epa"])
    print(f"Downloaded {len(rows)} team-game EPA rows; source nflverse via nflreadpy")

if __name__ == "__main__":
    main()
