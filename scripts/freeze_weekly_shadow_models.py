#!/usr/bin/env python3
"""Freeze ten comparable shadow forecasts from current pregame model components.

These are live-input shadow variants, NOT an exact replay of historical V3.
Only model-input fields available before kickoff are used.
"""
import json,datetime as dt,math,pathlib\nfrom itertools import product
ROOT=pathlib.Path(__file__).resolve().parents[1];DATA=ROOT/"data"
WEIGHTS={
 "live":(0,0,0,0),"baseline":(1,0,0,0),"workload":(0,1,0,0),
 "matchup":(0,0,1,0),"recent_form":(0,0,0,1),
 "baseline_workload_blend":(.5,.5,0,0),
 "workload_matchup_blend":(0,.5,.5,0),
 "baseline_matchup_blend":(.5,0,.5,0),
 "recent_matchup_blend":(0,0,.5,.5),
 "four_way_blend":(.25,.25,.25,.25)}
# Same candidate family on every eligible prop: all 25%-increment blends.
WEIGHTS.update({"mix_"+''.join(map(str,w)):tuple(v/4 for v in w)
                for w in product(range(5),repeat=4) if sum(w)==4})
def finite(x):
 try:
  n=float(x);return n if math.isfinite(n) else None
 except (ValueError,TypeError):return None
def build(source,snapshots,existing):
 indexed={(str(r.get("game_id")),str(r.get("player_id")),str(r.get("market_key") or r.get("market"))):r for r in source.get("players",[])}
 # Keep all previously frozen forecasts; never recalculate or overwrite a model/game/player/market.
 out={(str(r.get("game_id")),str(r.get("player_id")),str(r.get("stat_key")),str(r.get("model"))):r for r in existing}
 for snap in snapshots:
  key=(str(snap.get("game_id")),str(snap.get("player_id")),str(snap.get("market")))
  p=indexed.get(key)
  if not p:continue
  try:
   kickoff=dt.datetime.fromisoformat(snap["kickoff"].replace("Z","+00:00"))
   captured=dt.datetime.fromisoformat(snap["captured_at"].replace("Z","+00:00"))
   generated=dt.datetime.fromisoformat(source["generated_at_utc"].replace("Z","+00:00"))
   if not (generated<=captured<kickoff):continue
  except (KeyError,ValueError,TypeError):continue
  live=finite(snap.get("projection"));base=finite(p.get("base_projection"))
  defense=finite(p.get("defense_factor"));workload=finite(p.get("workload_factor"))
  recent=finite(p.get("recent_5_avg"))
  if None in (live,base,defense,workload):continue
  values=(base,base*workload,base*defense, recent if recent is not None else base)
  for name,weights in WEIGHTS.items():
   record_key=(*key,name)
   if record_key in out:continue
   projection=live if name=="live" else sum(v*w for v,w in zip(values,weights))
   out[record_key]={"game_id":key[0],"player_id":key[1],"stat_key":key[2],"model":name,
     "projection":round(max(0,projection),4),"dk_line":snap.get("dk_line"),
     "kickoff_utc":snap["kickoff"],"predicted_at_utc":snap["captured_at"],
     "source":"count-props pregame components","actual":None}
 return sorted(out.values(),key=lambda r:(r["game_id"],r["player_id"],r["stat_key"],r["model"]))
def main():
 source=json.loads((DATA/"count-projections.json").read_text())
 snapshots=json.loads((DATA/"pregame-snapshots.json").read_text()).get("records",[])
 path=DATA/"weekly-shadow-forecasts.json"
 old=json.loads(path.read_text()).get("rows",[]) if path.exists() else []
 rows=build(source,snapshots,old)
 if len(rows)<len(old):raise RuntimeError("Refusing to lose shadow forecasts")
 path.write_text(json.dumps({"schema_version":1,"description":"Frozen research-only live-input shadow model projections","rows":rows},indent=2)+"\n")
 print(f"Frozen shadow forecasts: {len(rows)} rows ({len(old)} previously saved)")
if __name__=="__main__":main()
