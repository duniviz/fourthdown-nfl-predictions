#!/usr/bin/env python3
"""Evidence-grounded, game-specific editorial previews; never modifies forecasts."""
import datetime as dt
import difflib
import json
import os
from pathlib import Path
import re
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"ai-game-previews.json"
UTC=dt.timezone.utc

def parse_time(value):
    try: return dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
    except (TypeError,ValueError): return None

def evidence(game,context):
    facts={}
    def put(key,value):
        if value is not None and value!="": facts[key]=value
    put("teams",{"away":game.get("away"),"home":game.get("home")})
    put("kickoff_utc",game.get("kickoff_utc"))
    put("model_projection",{"home_points":game.get("projected_home_score"),"away_points":game.get("projected_away_score"),"winner":game.get("predicted_winner")})
    for side in ("home","away"):
        model=(game.get("analysis") or {}).get(side) or {}
        put(side+"_model_rankings",{k:model[k] for k in ("offense_rank","defense_rank","offense_epa_rating","defense_epa_rating") if k in model})
        recent=(context.get("recent") or {}).get(side) or {}
        if recent.get("status")=="verified":
            put(side+"_recent_results",{k:recent[k] for k in ("wins","losses","ties","avg_points_for","avg_points_against","games") if k in recent})
        rest=(context.get("rest") or {}).get(side) or {}
        if rest.get("status")=="verified":
            put(side+"_rest",{k:rest[k] for k in ("days_since_last_game",) if k in rest})
    meetings=context.get("head_to_head") or {}
    if meetings.get("status")=="verified": put("previous_meetings",meetings.get("games",[])[:2])
    # Only verified availability; an unavailable report cannot support injury claims.
    availability=context.get("availability") or {}
    if availability.get("status")=="verified": put("verified_availability",availability)
    return facts

def generate(game_id,facts,existing):
    key=os.environ.get("OPENAI_API_KEY","")
    if not key: raise RuntimeError("OPENAI_API_KEY not configured")
    other_titles=[s["title"] for p in existing.values() for s in p.get("stories",[])]
    instructions=(
      "You are an experienced NFL beat writer, not a betting tipster. Write a natural, distinctive "
      "pregame preview for ONE game. No formulaic structure, repetitive headings, or generic claims. "
      "Find 2-5 genuinely noteworthy connections across supplied evidence, prioritizing what "
      "makes this game different. Use varying lengths and punchy, specific headlines. "
      "Never invent injuries, quarterback changes, coaching tendencies, line movement, player names, "
      "weather, statistics, or news. Do not infer an injury from unavailable availability. "
      "Treat model projections as estimates, not verified outcomes. "
      "Do not mention odds or line movement unless verified market history is supplied. "
      "If evidence is thin, write just 1-2 modestly scoped stories. "
      "Every story must cite 1-3 exact evidence keys from the input. "
      "Return JSON only: {\\\"headline\\\":string,\\\"stories\\\":[{\\\"title\\\":string,\\\"body\\\":string,\\\"evidence_keys\\\":[string]}]}. "
      "Each body 45-110 words. Avoid these other games' headlines: "+json.dumps(other_titles[-70:])
    )
    payload={"model":os.environ.get("FOURTHDOWN_PREVIEW_MODEL","gpt-4.1-mini"),
             "temperature":0.75,
             "messages":[{"role":"system","content":instructions},
                         {"role":"user","content":json.dumps({"game_id":game_id,"verified_evidence":facts})}],
             "response_format":{"type":"json_object"}}
    request=urllib.request.Request("https://api.openai.com/v1/chat/completions",
       data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(request,timeout=60) as response: result=json.load(response)
    return json.loads(result["choices"][0]["message"]["content"])

def validate(result,facts,existing):
    if not isinstance(result,dict) or not isinstance(result.get("headline"),str): return False
    stories=result.get("stories")
    if not isinstance(stories,list) or not 1<=len(stories)<=5: return False
    previous=[s.get("title","") for p in existing.values() for s in p.get("stories",[])]
    seen=[]
    for story in stories:
        if not isinstance(story,dict): return False
        title,body,keys=story.get("title"),story.get("body"),story.get("evidence_keys")
        if not isinstance(title,str) or not 8<=len(title)<=100: return False
        if not isinstance(body,str) or not 70<=len(body)<=1100: return False
        if not isinstance(keys,list) or not keys or not all(isinstance(k,str) and k in facts for k in keys): return False
        if any(difflib.SequenceMatcher(None,title.lower(),old.lower()).ratio()>0.80 for old in previous+seen): return False
        if re.search(r"\\b(?:sources say|reportedly|according to reports)\\b",body,re.I): return False
        seen.append(title)
    return True

def main():
    forecasts=json.loads((ROOT/"data/live-v2.json").read_text())
    contexts=json.loads((ROOT/"data/game-context.json").read_text()).get("games",{})
    now=dt.datetime.now(UTC)
    previous=json.loads(OUT.read_text()) if OUT.exists() else {"games":{}}
    saved=previous.get("games",{})
    changed=False
    for game in forecasts.get("games",[]):
        gid=game.get("game_id")
        kickoff=parse_time(game.get("kickoff_utc"))
        if not gid or not kickoff: continue
        minutes=(kickoff-now).total_seconds()/60
        if minutes<=30 or minutes>10080: continue # no after-lock rewriting
        facts=evidence(game,contexts.get(gid,{}) or {})
        if len(facts)<5: continue
        signature=json.dumps(facts,sort_keys=True)
        if saved.get(gid,{}).get("evidence_signature")==signature: continue
        try:
            result=generate(gid,facts,saved)
            if not validate(result,facts,saved):
                print("Rejected ungrounded or repetitive preview",gid)
                continue
        except Exception as exc:
            print("Preview unavailable for",gid,type(exc).__name__,str(exc)[:120])
            continue
        saved[gid]={"headline":result["headline"],"stories":result["stories"],
                    "evidence_signature":signature,"generated_at_utc":now.isoformat(),
                    "kickoff_utc":game["kickoff_utc"],"source":"AI editorial draft from saved model and verified ESPN context"}
        changed=True
    if changed:
        OUT.write_text(json.dumps({"schema_version":1,"games":saved},indent=2,ensure_ascii=False)+"\\n")
        print("Updated verified preview drafts")
    else: print("No verified previews updated")

if __name__=="__main__": main()
