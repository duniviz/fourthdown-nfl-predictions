#!/usr/bin/env python3
"""Audit completed games without manufacturing historical predictions or DK prices."""
import json,pathlib,collections,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]/"data"
def load(name):
 try:return json.loads((ROOT/name).read_text())
 except (OSError,ValueError):return {}
def parse(v):
 try:return datetime.datetime.fromisoformat(str(v).replace("Z","+00:00"))
 except (TypeError,ValueError):return None
def audit():
 results=load("player-results.json").get("rows",[])
 snapshots=load("pregame-snapshots.json").get("records",[])
 quotes=load("dk-pregame-lines.json").get("rows",[])
 out=[]
 for week in ("2026_07","2026_08"):
  actual=[r for r in results if str(r.get("game_id","")).startswith(week+"_")]
  games=sorted({str(r["game_id"]) for r in actual})
  snap=[r for r in snapshots if str(r.get("game_id","")).startswith(week+"_")]
  valid=[r for r in snap if parse(r.get("captured_at")) and parse(r.get("kickoff")) and parse(r["captured_at"])<parse(r["kickoff"])]
  dk=[r for r in valid if r.get("dk_line") is not None and parse(r.get("dk_captured_at")) and parse(r["dk_captured_at"])<parse(r["kickoff"])]
  print(f'{week}: games={len(games)}, historical_actual_rows={len(actual)}, verified_pregame_projections={len(valid)}, verified_DK_lines={len(dk)}')
  for game in games:print(f'  {game}: actual_rows={sum(r.get("game_id")==game for r in actual)}')
  out.append(dict(week=week,games=len(games),actual_rows=len(actual),verified_pregame=len(valid),verified_dk=len(dk)))
 print(f'Other saved DK pregame rows: {len(quotes)} (not trusted without independent timestamp verification)')
 return out
if __name__=="__main__":audit()
