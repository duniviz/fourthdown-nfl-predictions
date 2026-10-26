"""Publish current NFL team injury reports without guessing player availability.

ESPN injury endpoint is best-effort and may omit unreported/late-breaking news.
A missing report never means a healthy roster. This module does not change scores.
"""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TEAMS=("ARI","ATL","BAL","BUF","CAR","CHI","CIN","CLE","DAL","DEN","DET","GB","HOU","IND","JAX","KC","LAC","LAR","LV","MIA","MIN","NE","NO","NYG","NYJ","PHI","PIT","SEA","SF","TB","TEN","WSH")
ALIASES={"JAX":"JAC","WSH":"WAS"}
def load(team):
    url="https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/"+team.lower()+"/injuries"
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 FOURTHDOWN injury research","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=12) as response:
        return json.load(response)

def entries(obj):
    # Preserve raw ESPN statuses; never infer game availability from a generic injury label.
    seen=set()
    def walk(node):
        if isinstance(node,list):
            for item in node: yield from walk(item)
        elif isinstance(node,dict):
            athlete=node.get("athlete")
            if isinstance(athlete,dict) and ("status" in node or "type" in node):
                name=athlete.get("displayName") or athlete.get("fullName")
                if name:
                    status=node.get("status")
                    if isinstance(status,dict): status=status.get("name") or status.get("description")
                    typ=node.get("type")
                    if isinstance(typ,dict): typ=typ.get("description") or typ.get("name")
                    detail=node.get("details") or {}
                    if not isinstance(detail,dict): detail={}
                    key=(str(athlete.get("id") or name),str(status or typ))
                    if key not in seen:
                        seen.add(key)
                        yield {"player":str(name),"position":str((athlete.get("position") or {}).get("abbreviation","") if isinstance(athlete.get("position"),dict) else athlete.get("position") or ""),"status":str(status or typ or "Reported injury"),"detail":str(detail.get("detail") or detail.get("type") or "")[:160]}
            for v in node.values(): yield from walk(v)
    return list(walk(obj))

def main():
    data={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"source":"ESPN team injury reports","model_adjusted":False,"teams":{}}
    ok=0
    # Prefer the league-wide report: one consistent snapshot and less risk of
    # team-code mismatch. Fall back to team feeds when unavailable.
    try:
        req=urllib.request.Request("https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries",headers={"User-Agent":"Mozilla/5.0 FOURTHDOWN","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=15) as response:
            league=json.load(response)
        blocks=league.get("injuries",[])
        for block in blocks:
            team=(block.get("team") or {}).get("abbreviation","").upper()
            team=ALIASES.get(team,team)
            if team:
                data["teams"][team]={"status":"retrieved","players":entries(block.get("injuries",[]))}
        ok=len(data["teams"])
    except Exception:
        pass
    for team in TEAMS:
        code=ALIASES.get(team,team)
        if code in data["teams"]: continue
        try:
            raw=load(team)
            rows=entries(raw)
            data["teams"][code]={"status":"retrieved","players":rows}
            ok+=1
        except Exception as e:
            data["teams"][ALIASES.get(team,team)]={"status":"unavailable","players":[]}
    if not ok: raise RuntimeError("All injury feeds unavailable: do not overwrite prior data")
    Path("data").mkdir(exist_ok=True)
    Path("data/injuries.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print(f"Fetched {ok}/{len(TEAMS)} team injury reports")
if __name__=="__main__": main()
