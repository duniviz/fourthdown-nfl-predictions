#!/usr/bin/env python3
"""Free, evidence-grounded matchup previews. No external AI service or API charges."""
import json
import urllib.request
import xml.etree.ElementTree as ET
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode, urlparse
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from pathlib import Path
try:
    from tools.sourced_matchup_context import collect as collect_sourced_context
except ModuleNotFoundError:
    from sourced_matchup_context import collect as collect_sourced_context

ROOT = Path(__file__).resolve().parents[1]
FORECAST = ROOT / "data/live-v2.json"
OUTPUT = ROOT / "data/ai-game-previews.json"

TEAM_NAMES = {
"ARI":"Arizona Cardinals","ATL":"Atlanta Falcons","BAL":"Baltimore Ravens","BUF":"Buffalo Bills",
"CAR":"Carolina Panthers","CHI":"Chicago Bears","CIN":"Cincinnati Bengals","CLE":"Cleveland Browns",
"DAL":"Dallas Cowboys","DEN":"Denver Broncos","DET":"Detroit Lions","GB":"Green Bay Packers",
"HOU":"Houston Texans","IND":"Indianapolis Colts","JAX":"Jacksonville Jaguars","KC":"Kansas City Chiefs",
"LAC":"Los Angeles Chargers","LAR":"Los Angeles Rams","LA":"Los Angeles Rams","LV":"Las Vegas Raiders",
"MIA":"Miami Dolphins","MIN":"Minnesota Vikings","NE":"New England Patriots","NO":"New Orleans Saints",
"NYG":"New York Giants","NYJ":"New York Jets","PHI":"Philadelphia Eagles","PIT":"Pittsburgh Steelers",
"SEA":"Seattle Seahawks","SF":"San Francisco 49ers","TB":"Tampa Bay Buccaneers",
"TEN":"Tennessee Titans","WSH":"Washington Commanders"
}

def matchup_news(game, now, fetch=None):
    """Read recent matchup-specific Google News RSS headlines, not articles."""
    aliases={"JAC":"JAX","WAS":"WSH","LAR":"LA"}
    away=TEAM_NAMES.get(aliases.get(game.get("away"),game.get("away")))
    home=TEAM_NAMES.get(aliases.get(game.get("home"),game.get("home")))
    if not away or not home: return []
    query=urlencode({"q":away+" "+home+" NFL matchup", "hl":"en-US", "gl":"US", "ceid":"US:en"})
    url="https://news.google.com/rss/search?"+query
    try:
        if fetch is None:
            req=urllib.request.Request(url,headers={"User-Agent":"FOURTHDOWN-News/1.0"})
            with urllib.request.urlopen(req,timeout=5) as response:
                raw=response.read(400000)
        else: raw=fetch(url)
        root=ET.fromstring(raw)
        result=[]; seen=set()
        for item in root.findall(".//item"):
            title=(item.findtext("title") or "").strip()
            link=(item.findtext("link") or "").strip()
            publisher=(item.findtext("source") or "News").strip()
            try: published=parsedate_to_datetime(item.findtext("pubDate") or "").astimezone(timezone.utc)
            except (TypeError,ValueError,OverflowError): continue
            if not 0 <= (now-published).total_seconds() <= 7*86400: continue
            parsed=urlparse(link)
            if parsed.scheme!="https" or parsed.hostname!="news.google.com": continue
            # Both nicknames in the title avoid unrelated single-team articles.
            title_lower=title.lower()
            if not all(re.search(r"(?<!\w)"+re.escape(name.split()[-1].lower())+r"(?!\w)",title_lower) for name in (away,home)): continue
            if not title or title_lower in seen: continue
            seen.add(title_lower)
            result.append({"title":title[:180],"url":link,"published_at_utc":published.isoformat(),"publisher":publisher[:100]})
            if len(result)>=4: break
        return result
    except (OSError,ET.ParseError,ValueError):
        return []

def fetch_news(now):
    """Public RSS headlines only; never copy articles or infer injury facts."""
    url="https://www.espn.com/espn/rss/nfl/news"
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"FOURTHDOWN-News/1.0"})
        with urllib.request.urlopen(req,timeout=12) as response:
            root=ET.fromstring(response.read(600000))
        articles=[]
        for item in root.findall(".//item"):
            title=(item.findtext("title") or "").strip()
            link=(item.findtext("link") or "").strip()
            pub=(item.findtext("pubDate") or "").strip()
            if not title or not link.startswith("https://www.espn.com/"):
                continue
            try: published=parsedate_to_datetime(pub).astimezone(timezone.utc)
            except (TypeError,ValueError): continue
            if not 0 <= (now-published).total_seconds() <= 7*86400: continue
            articles.append({"title":title[:180],"url":link,"published_at_utc":published.isoformat(),"publisher":"ESPN"})
        print("Fresh public ESPN RSS headlines:",len(articles))
        return articles
    except (OSError,ET.ParseError,ValueError) as exc:
        print("News feed unavailable; preserving model previews:",type(exc).__name__)
        return []

def relevant_news(game,articles):
    teams=[TEAM_NAMES.get(game["home"],""),TEAM_NAMES.get(game["away"],"")]
    matches=[]
    for item in articles:
        title=item["title"]
        if any(name and (name.split()[-1].lower() in title.lower() or name.lower() in title.lower()) for name in teams):
            matches.append(item)
    return matches[:4]

def describe(game):
    home, away = game["home"], game["away"]
    hp, ap = float(game["projected_home_score"]), float(game["projected_away_score"])
    h, a = game["analysis"]["home"], game["analysis"]["away"]
    hf, af = h.get("recent_form") or {}, a.get("recent_form") or {}
    winner = home if hp >= ap else away
    margin = abs(hp-ap)
    off_gap = abs(int(h["offense_rank"])-int(a["offense_rank"]))
    form_gap = abs(int(hf.get("wins",0))-int(af.get("wins",0)))
    if margin <= 2.5:
        headline = f"{away} at {home}: a forecast with almost no separation"
        title = "The narrowest of margins"
        angle = "A single red-zone stop or short-field possession could matter more than the projected edge."
    elif off_gap >= 12:
        headline = f"{away} at {home}: contrasting offenses shape the outlook"
        title = "Where the offenses diverge"
        angle = "The offensive efficiency gap is worth watching, although it does not guarantee a scoring gap of the same size."
    elif form_gap >= 3:
        headline = f"{away} at {home}: recent momentum meets the model"
        title = "Form versus forecast"
        angle = "The recent win totals are a useful cross-check, but a five-game sample cannot settle this matchup."
    else:
        headline = f"{away} at {home}: the details behind the projected edge"
        title = "A closer look at the forecast"
        angle = "The projection is a starting point, not a guarantee; a few high-leverage possessions could change the result."
    story1 = (f"FOURTHDOWN has {winner} ahead in this matchup, projecting {away} {ap:.1f} and "
              f"{home} {hp:.1f}, a {margin:.1f}-point difference. {angle} "
              f"The forecast reflects saved pregame model inputs rather than live game information.")
    story2 = (f"{home} ranks {h['offense_rank']} of 32 on offense and {h['defense_rank']} on defense "
              f"in the model; {away} ranks {a['offense_rank']} offensively and {a['defense_rank']} defensively. "
              f"Across their latest {hf.get('games','available')} and {af.get('games','available')} games, "
              f"respectively, {home} won {hf.get('wins','an unavailable number')} and {away} won "
              f"{af.get('wins','an unavailable number')}. These figures help frame the matchup, "
              f"but do not verify injuries, lineup changes, or late news.")
    return {"headline":headline,"stories":[
        {"title":title,"body":story1,"evidence_keys":["teams","model_projection"]},
        {"title":"What the efficiency and form numbers show","body":story2,
         "evidence_keys":["home_model_rankings","away_model_rankings"]}]}

def main():
    forecasts=json.loads(FORECAST.read_text())
    previous=json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {"games":{}}
    old=previous.get("games",{})
    updated={}
    now=datetime.now(timezone.utc)
    articles=fetch_news(now)
    upcoming=[]
    for game in forecasts.get("games",[]):
        try:
            kickoff=datetime.fromisoformat(game.get("kickoff_utc","").replace("Z","+00:00"))
            if kickoff > now and game.get("game_id"): upcoming.append(game)
        except (TypeError,ValueError): continue
    with ThreadPoolExecutor(max_workers=4) as pool:
        found=list(pool.map(lambda game: matchup_news(game,now),upcoming))
    matchup_articles={game["game_id"]:news for game,news in zip(upcoming,found)}
    try:
        scoreboard=json.loads((ROOT/"data/espn-scoreboard-backup.json").read_text())
        sourced=collect_sourced_context(upcoming,scoreboard,now)
        print("ESPN sourced matchups:",sum(bool(x) for x in sourced.values()))
    except Exception as exc:  # Optional context must never block the forecast refresh.
        print("Optional ESPN context unavailable:",type(exc).__name__)
        sourced={}
    for game in forecasts.get("games",[]):
        gid=game.get("game_id")
        if not gid or not game.get("kickoff_utc") or not game.get("analysis"):
            continue
        kickoff=datetime.fromisoformat(game["kickoff_utc"].replace("Z","+00:00"))
        prior=old.get(gid)
        news=matchup_articles.get(gid,[])+relevant_news(game,articles)
        news=news[:4]
        # Preserve existing editorial writing when projections and kickoff have not changed.
        signature=json.dumps({"kickoff":game["kickoff_utc"],"home":game["home"],
          "away":game["away"],"scores":[game["projected_home_score"],game["projected_away_score"]],
          "analysis":game["analysis"]},sort_keys=True)
        if kickoff <= now:
            if prior: updated[gid]=prior
            continue
        if prior and (prior.get("free_evidence_signature")==signature or
                      (not prior.get("free_evidence_signature") and prior.get("kickoff_utc")==game["kickoff_utc"])):
            updated[gid]={**prior,"news":news if news else prior.get("news",[]),
                          "external_context":sourced.get(gid) or prior.get("external_context")}
            continue
        updated[gid]={**describe(game),"generated_at_utc":now.isoformat(),
            "kickoff_utc":game["kickoff_utc"],"free_evidence_signature":signature,
            "source":"Free evidence-based model commentary (not generative AI)","news":news,
            "external_context":sourced.get(gid) or (prior or {}).get("external_context")}
    result={"schema_version":1,"games":updated}
    serialized=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
    if not OUTPUT.exists() or OUTPUT.read_text()!=serialized:
        OUTPUT.write_text(serialized)
    print(f"Free previews available: {len(updated)} for forecast week {forecasts.get('week')}")
    if not updated: raise SystemExit("No previews generated for current forecast slate")

if __name__=="__main__":
    main()


