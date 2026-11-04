#!/usr/bin/env python3
"""Grade frozen pregame yardage and game forecasts on identical slates."""
import json,pathlib,sys,urllib.request
from itertools import product
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"research"))
from same_slate_leaderboard import compare
from join_frozen_pregame_results import norm
MARKETS={"passing_yards","rushing_yards","receiving_yards","game_margin_home","game_total"}
EXPECTED={"live",*("mix_"+''.join(map(str,w)) for w in product(range(5),repeat=4) if sum(w)==4)}
def main():
 data=ROOT/"data"
 archive=json.loads((data/"weekly-shadow-forecasts.json").read_text()).get("rows",[])
 finals=json.loads((data/"player-results.json").read_text()).get("rows",[])
 actuals={(str(r.get("game_id")),str(r.get("player_id")),norm(r.get("stat_key"))):r["actual"]
          for r in finals if r.get("player_id") and r.get("actual") is not None and not r.get("dnp") and r.get("played") is not False}
 games={r["game_id"] for r in archive if r.get("stat_key") in ("game_margin_home","game_total")}
 by_week={}
 for game in games:
  try:
   year,week=game.split("_")[:2];by_week.setdefault((year,week),set()).add(game)
  except ValueError:continue
 for (year,week),ids in by_week.items():
  try:
   url=f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={year}&seasontype=2&week={int(week)}&limit=100"
   with urllib.request.urlopen(url,timeout=20) as response:events=json.load(response).get("events",[])
   for e in events:
    comp=(e.get("competitions") or [{}])[0]
    if not (comp.get("status",{}).get("type",{}).get("completed") or e.get("status",{}).get("type",{}).get("completed")):continue
    sides={c.get("homeAway"):c for c in comp.get("competitors",[])}
    h=sides.get("home",{});a=sides.get("away",{})
    home=h.get("team",{}).get("abbreviation");away=a.get("team",{}).get("abbreviation")
    game=f"{year}_{int(week):02d}_{away}_{home}"
    if game not in ids:continue
    hs=float(h["score"]);aws=float(a["score"])
    actuals[(game,"GAME","game_margin_home")]=hs-aws
    actuals[(game,"GAME","game_total")]=hs+aws
  except (OSError,ValueError,KeyError,TimeoutError) as exc:print("Final game scores unavailable:",exc)
 groups={}
 for r in archive:
  market=norm(r.get("stat_key"))
  if market not in MARKETS:continue
  key=(str(r.get("game_id")),str(r.get("player_id")),market)
  if key not in actuals:continue
  groups.setdefault(key,[]).append(dict(r,stat_key=market,actual=actuals[key]))
 # Game models have a different candidate family than player-yardage models.
 # Require the incumbent plus all three ML challengers for an exact paired slate.
 game_models={"live","ml_ridge","ml_random_forest","ml_gradient_boosting"}
 complete=[r for key,group in groups.items()
           if (game_models if key[2] in ("game_margin_home","game_total") else EXPECTED).issubset({r["model"] for r in group})
           for r in group]
 report=compare(complete)
 report["status"]="COMPLETE" if report["matched_slate_records"] else ("WAITING_FOR_FINALS" if groups else "WAITING_FOR_PREGAME_OR_FINALS")
 report["coverage"]={"verified_market_rows":len(groups),"complete_market_rows":len({(r["game_id"],r["player_id"],r["stat_key"]) for r in complete}),"required_models":len(EXPECTED)}
 out=ROOT/"research"/"yardage-game-results";out.mkdir(parents=True,exist_ok=True)
 (out/"leaderboard.json").write_text(json.dumps(report,indent=2)+"\n")
 lines=["# Yardage and game same-slate research",f"Status: {report['status']}",f"Complete game/player/market comparisons: {report['matched_slate_records']}","",
        "| Market | Model | N | MAE | RMSE | DK N | DK hit % |","|---|---|---:|---:|---:|---:|---:|"]
 for r in report["metrics"]:
  hit="—" if r["dk_hit_rate"] is None else f'{r["dk_hit_rate"]*100:.1f}%'
  lines.append(f'| {r["market"]} | {r["model"]} | {r["n"]} | {r["mae"]} | {r["rmse"]} | {r["dk_n"]} | {hit} |')
 lines+=["","Research only. Game comparisons now require frozen incumbent plus three ML challengers on identical games. QB PAR is not yet a deployable pregame challenger. No production promotion."]
 (out/"RESULTS.md").write_text("\n".join(lines)+"\n")
 print("\n".join(lines))
if __name__=="__main__":main()
