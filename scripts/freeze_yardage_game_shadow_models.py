#!/usr/bin/env python3
"""Freeze same-slate research variants for yards and game margin/total before kickoff."""
import datetime as dt,json,math,pathlib
from itertools import product
ROOT=pathlib.Path(__file__).resolve().parents[1]; DATA=ROOT/"data"
UTC=dt.timezone.utc
def load(name):
 try:return json.loads((DATA/name).read_text())
 except (OSError,ValueError):return {}
def parse(x):
 try:return dt.datetime.fromisoformat(str(x).replace("Z","+00:00")).astimezone(UTC)
 except (TypeError,ValueError):return None
def number(x):
 try:
  x=float(x);return x if math.isfinite(x) else None
 except (ValueError,TypeError):return None
WEIGHTS={"mix_"+''.join(map(str,w)):tuple(v/4 for v in w) for w in product(range(5),repeat=4) if sum(w)==4}
WEIGHTS["live"]=(0,0,0,0)
def variants(key,values,live,kickoff,predicted,dk_line,source,now):
 if None in values or live is None:return []
 return [dict(key,model=name,projection=round(max(0,v),4) if key["stat_key"] not in ("game_margin_home",) else round(v,4),
              dk_line=dk_line,kickoff_utc=kickoff,predicted_at_utc=now.isoformat(),source_forecast_at_utc=predicted,source=source,actual=None)
         for name,w in WEIGHTS.items()
         for v in [live if name=="live" else sum(a*b for a,b in zip(values,w))]]
def build(now=None):
 now=now or dt.datetime.now(UTC)
 archive=load("weekly-shadow-forecasts.json")
 old=archive.get("rows",[])
 indexed={(str(r.get("game_id")),str(r.get("player_id")),str(r.get("stat_key")),str(r.get("model"))):r for r in old}
 games=load("live-v2.json"); stamp=parse(games.get("generated_at_utc"))
 game_by_team={}
 for g in games.get("games",[]):
  game_by_team[(g.get("home"),g.get("away"))]=g
  kickoff=parse(g.get("kickoff_utc"))
  if not stamp or not kickoff or not stamp<kickoff or now>=kickoff or stamp>now:continue
  home=number(g.get("projected_home_score"));away=number(g.get("projected_away_score"))
  analysis=g.get("analysis") or {};h=analysis.get("home") or {};a=analysis.get("away") or {}
  hr=(h.get("recent_form") or {});ar=(a.get("recent_form") or {})
  if None in (home,away):continue
  margin=home-away;total=home+away
  recent_margin=number(hr.get("avg_margin"));away_recent=number(ar.get("avg_margin"))
  recent_home=number(hr.get("avg_points_for"));recent_away=number(ar.get("avg_points_for"))
  # Components are transparent pregame heuristics, not historical V3 forecasts.
  margin_components=(margin, (recent_margin-away_recent)/2 if None not in (recent_margin,away_recent) else margin,
                     margin*.8,margin*.5)
  total_components=(total, (recent_home+recent_away) if None not in (recent_home,recent_away) else total,
                    total*.95,total*1.05)
  for market,vals,live in [("game_margin_home",margin_components,margin),("game_total",total_components,total)]:
   for r in variants({"game_id":g["game_id"],"player_id":"GAME","stat_key":market},vals,live,kickoff.isoformat(),stamp.isoformat(),None,"live-v2 pregame game metrics",now):
    key=(r["game_id"],r["player_id"],r["stat_key"],r["model"]);indexed.setdefault(key,r)
 desk=load("research-prop-desk.json");dstamp=parse(desk.get("generated_at_utc"))
 if dstamp and dstamp<=now:
  for p in desk.get("comparisons",[]):
   market=p.get("market")
   if market not in ("passing_yards","rushing_yards","receiving_yards"):continue
   team=p.get("team");opp=p.get("opponent")
   # Match team/opponent to an actual scheduled game, never infer a game id from week alone.
   g=next((g for g in games.get("games",[]) if {g.get("home"),g.get("away")}=={team,opp}),None)
   if not g:continue
   kickoff=parse(g.get("kickoff_utc"))
   if not kickoff or dstamp>=kickoff or now>=kickoff:continue
   player=p.get("player_id");live=number(p.get("projected_yards"))
   if not player or live is None:continue
   line=number(p.get("dk_line"));line_time=parse(p.get("last_update"))
   if not line_time or line_time>=kickoff or line_time>dstamp:line=None
   # Independent input variants based on the same pregame projection.
   # Do not claim these are separate trained historical models.
   values=(live,live*.9,live*1.1,live*.95)
   for r in variants({"game_id":g["game_id"],"player_id":player,"stat_key":market},values,live,kickoff.isoformat(),dstamp.isoformat(),line,"research-prop-desk pregame projection sensitivity grid",now):
    key=(r["game_id"],r["player_id"],r["stat_key"],r["model"]);indexed.setdefault(key,r)
 return sorted(indexed.values(),key=lambda r:(r["game_id"],r["player_id"],r["stat_key"],r["model"]))
def main():
 path=DATA/"weekly-shadow-forecasts.json";rows=build()
 path.write_text(json.dumps({"schema_version":2,"description":"Immutable research-only pregame forecasts for eligible count, yardage, and game markets","rows":rows},indent=2)+"\n")
 from collections import Counter
 print("Frozen shadow rows:",len(rows),"by market:",dict(Counter(r["stat_key"] for r in rows)))
if __name__=="__main__":main()
