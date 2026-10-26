"""Retrieve NFL scoreboard snapshots for the FOURTHDOWN website.

ESPN public scoreboard feed is a best-effort source, not an official real-time
NFL feed. Never replace a good snapshot with an error response.
"""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL="https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

def main():
    request=urllib.request.Request(URL,headers={"User-Agent":"FOURTHDOWN/1.0 (scoreboard aggregator)","Accept":"application/json"})
    with urllib.request.urlopen(request,timeout=25) as response:
        raw=json.load(response)
    games=[]
    for event in raw.get("events",[]):
        competitions=event.get("competitions") or []
        if not competitions: continue
        competition=competitions[0]
        competitors=competition.get("competitors") or []
        home=next((x for x in competitors if x.get("homeAway")=="home"),None)
        away=next((x for x in competitors if x.get("homeAway")=="away"),None)
        if not home or not away: continue
        status=competition.get("status") or event.get("status") or {}
        st=status.get("type") or {}
        def team(x):
            t=x.get("team") or {}
            return {"abbr":t.get("abbreviation",""),"name":t.get("displayName",""),
                    "logo":t.get("logo",""),"score":x.get("score",None),
                    "record":next((v.get("summary") for v in x.get("records",[]) if v.get("type")=="total"),"")}
        games.append({"id":str(event.get("id","")),"date":event.get("date"),
            "name":event.get("name",""),"home":team(home),"away":team(away),
            "state":st.get("state","pre"),"status":st.get("shortDetail") or st.get("detail") or "",
            "period":status.get("period",0),"clock":status.get("displayClock",""),
            "broadcast":", ".join((x.get("names") or [])[:2][0] for x in competition.get("broadcasts",[]) if x.get("names")),
            "link":"https://www.espn.com/nfl/game/_/gameId/"+str(event.get("id",""))})
    if not games: raise RuntimeError("Scoreboard source returned no games; retain prior snapshot")
    output={"source":"ESPN scoreboard","updated_at_utc":datetime.now(timezone.utc).isoformat(),
            "note":"Scores may be delayed. Refreshes depend on source availability and scheduled GitHub Actions.",
            "games":games}
    target=Path("data/live-scores.json")
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")
    print(f"Saved {len(games)} NFL games at {output['updated_at_utc']}")

if __name__=="__main__":main()
