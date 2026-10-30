"""Historical team game-script tendencies from nflverse play-by-play.
Usage: pip install pandas pyarrow requests
       python research/build_blowout_tendencies.py --seasons 2023 2024 2025
Outputs are descriptive, not validated future player projections.
"""
import argparse
from pathlib import Path
import pandas as pd

FIELDS = ["season","week","game_id","play_id","posteam","defteam","qtr",
          "score_differential","game_seconds_remaining","pass","rush",
          "qb_dropback","pass_attempt","rush_attempt","passing_yards",
          "rushing_yards","receiving_yards","passer_player_id",
          "rusher_player_id","receiver_player_id"]
def score_bucket(diff):
    if diff <= -28: return "trail_28_plus"
    if diff <= -21: return "trail_21_27"
    if diff <= -14: return "trail_14_20"
    if diff <= -7: return "trail_7_13"
    if diff < 7: return "within_6"
    if diff < 14: return "lead_7_13"
    if diff < 21: return "lead_14_20"
    if diff < 28: return "lead_21_27"
    return "lead_28_plus"

def run(seasons, out):
    frames=[]
    for season in seasons:
        url=f"https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet"
        try:
            df=pd.read_parquet(url, columns=FIELDS)
        except Exception as exc:
            print(f"Skipping {season}: {exc}")
            continue
        df=df[(df.qtr.between(1,4)) & df.posteam.notna() &
              df.score_differential.notna() & df.game_seconds_remaining.notna()].copy()
        df["pass_play"]=pd.to_numeric(df["pass"],errors="coerce").fillna(0).eq(1)
        df["rush_play"]=pd.to_numeric(df["rush"],errors="coerce").fillna(0).eq(1)
        df=df[df.pass_play | df.rush_play].copy()
        df["score_bucket"]=df.score_differential.map(score_bucket)
        df["quarter"]=df.qtr.astype(int)
        df["half"]=df.quarter.map(lambda q:"H1" if q<=2 else "H2")
        df["pass_play"]=df.pass_play.astype(int)
        df["rush_play"]=df.rush_play.astype(int)
        frames.append(df)
    if not frames: raise RuntimeError("No season data retrieved; no report generated")
    df=pd.concat(frames,ignore_index=True)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    grouping=["season","posteam","score_bucket","quarter"]
    stats=(df.groupby(grouping,observed=True)
           .agg(pass_plays=("pass_play","sum"),rush_plays=("rush_play","sum"),
                scrimmage_plays=("play_id","size") if "play_id" in df else ("pass_play","size"),
                distinct_games=("game_id","nunique"))
           .reset_index())
    stats["pass_rate"]=stats.pass_plays/stats.scrimmage_plays
    stats["rush_rate"]=stats.rush_plays/stats.scrimmage_plays
    stats.to_csv(out/"team_score_script_by_quarter.csv",index=False)
    league=(df.groupby(["score_bucket","quarter"],observed=True)
            .agg(pass_plays=("pass_play","sum"),rush_plays=("rush_play","sum"),
                 plays=("pass_play","size"),games=("game_id","nunique")).reset_index())
    league["pass_rate"]=league.pass_plays/league.plays
    league.to_csv(out/"league_score_script_by_quarter.csv",index=False)
    print(f"Wrote {len(stats)} team rows and {len(league)} league rows; {len(df)} qualifying plays")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--seasons",type=int,nargs="+",default=[2023,2024,2025])
    p.add_argument("--out",default="reports/blowout_game_script")
    a=p.parse_args()
    run(a.seasons,a.out)
