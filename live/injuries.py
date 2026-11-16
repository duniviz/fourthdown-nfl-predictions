"""Publish current NFL team injury reports without guessing player availability.

ESPN injury endpoint is best-effort and may omit unreported/late-breaking news.
A missing report never means a healthy roster. This module does not change scores.

The league feed is the source of truth. Its blocks are {id, displayName, injuries}
with no nested team object (confirmed against the live payload on 2026-11-16).
Older payloads that nested team.abbreviation are still accepted. A per-team
response of {} is an empty feed, not a successful retrieval.
"""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TEAMS=("ARI","ATL","BAL","BUF","CAR","CHI","CIN","CLE","DAL","DEN","DET","GB","HOU","IND","JAX","KC","LAC","LAR","LV","MIA","MIN","NE","NO","NYG","NYJ","PHI","PIT","SEA","SF","TB","TEN","WSH")
# Historical one-way remap. Publishing now stores every equivalent code instead,
# so nflverse (JAX, LA, WAS) and ESPN/site codes (JAC, LAR, WSH) both resolve.
ALIASES={"JAX":"JAC","WSH":"WAS"}
EQUIVALENT={
    "JAX":("JAX","JAC"),"JAC":("JAX","JAC"),
    "WAS":("WAS","WSH"),"WSH":("WAS","WSH"),
    "LA":("LA","LAR"),"LAR":("LA","LAR"),
}
TEAM_NAMES={
    "Arizona Cardinals":"ARI","Atlanta Falcons":"ATL","Baltimore Ravens":"BAL",
    "Buffalo Bills":"BUF","Carolina Panthers":"CAR","Chicago Bears":"CHI",
    "Cincinnati Bengals":"CIN","Cleveland Browns":"CLE","Dallas Cowboys":"DAL",
    "Denver Broncos":"DEN","Detroit Lions":"DET","Green Bay Packers":"GB",
    "Houston Texans":"HOU","Indianapolis Colts":"IND","Jacksonville Jaguars":"JAX",
    "Kansas City Chiefs":"KC","Las Vegas Raiders":"LV","Los Angeles Chargers":"LAC",
    "Los Angeles Rams":"LAR","Miami Dolphins":"MIA","Minnesota Vikings":"MIN",
    "New England Patriots":"NE","New Orleans Saints":"NO","New York Giants":"NYG",
    "New York Jets":"NYJ","Philadelphia Eagles":"PHI","Pittsburgh Steelers":"PIT",
    "San Francisco 49ers":"SF","Seattle Seahawks":"SEA","Tampa Bay Buccaneers":"TB",
    "Tennessee Titans":"TEN","Washington Commanders":"WAS",
}
# ESPN team ids on the league injuries feed, verified 2026-11-16.
ESPN_IDS={
    "22":"ARI","1":"ATL","33":"BAL","2":"BUF","29":"CAR","3":"CHI","4":"CIN",
    "5":"CLE","6":"DAL","7":"DEN","8":"DET","9":"GB","34":"HOU","11":"IND",
    "30":"JAX","12":"KC","13":"LV","24":"LAC","14":"LAR","15":"MIA","16":"MIN",
    "17":"NE","18":"NO","19":"NYG","20":"NYJ","21":"PHI","23":"PIT","25":"SF",
    "26":"SEA","27":"TB","10":"TEN","28":"WAS",
}

class InjuryPublishError(RuntimeError):
    """League feed contained players but the parsed output did not."""

def codes_for(team):
    team=str(team or "").upper()
    if not team: return ()
    return EQUIVALENT.get(team,(team,))

def store_team(bucket, team, payload):
    for code in codes_for(team):
        bucket[code]=payload

def lookup_report(reports, team):
    """Resolve a report stored under nflverse or ESPN abbreviations."""
    if not isinstance(reports, dict): return {}
    found={}
    for code in codes_for(team):
        report=reports.get(code)
        if not isinstance(report, dict): continue
        if report.get("players"): return report
        if not found: found=report
    return found

def team_from_block(block):
    """Resolve a league-feed block to a team abbreviation.

    Current ESPN league blocks are {id, displayName, injuries}. Older payloads
    that included team.abbreviation or team.displayName still resolve.
    """
    if not isinstance(block, dict): return ""
    team=block.get("team") if isinstance(block.get("team"), dict) else {}
    for source in (team, block):
        abbr=str(source.get("abbreviation") or source.get("abbrev") or "").upper()
        if abbr: return abbr
    for source in (team, block):
        name=str(source.get("displayName") or source.get("name") or "").strip()
        if name in TEAM_NAMES: return TEAM_NAMES[name]
    best=""; best_len=0
    for source in (team, block):
        lowered=str(source.get("displayName") or source.get("name") or "").strip().lower()
        if not lowered: continue
        for full, abbr in TEAM_NAMES.items():
            if full.lower() in lowered and len(full)>best_len:
                best, best_len=abbr, len(full)
    if best: return best
    return ESPN_IDS.get(str(block.get("id") or team.get("id") or ""), "")

def load(team):
    url="https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/"+str(team).lower()+"/injuries"
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

def report_from_payload(raw):
    """A retrieved report must contain players. {} is empty, not a success."""
    rows=entries(raw)
    if rows: return {"status":"retrieved","players":rows}
    return {"status":"empty","players":[]}

def apply_league_feed(data, league):
    """Parse a league-wide ESPN injuries payload into data['teams'].

    Returns how many teams received at least one player. Empty blocks are
    stored as status "empty" and never as a successful retrieval.
    """
    blocks=league.get("injuries",[]) if isinstance(league, dict) else []
    filled=set()
    teams=data.setdefault("teams",{})
    for block in blocks:
        if not isinstance(block, dict): continue
        team=team_from_block(block)
        if not team: continue
        report=report_from_payload(block.get("injuries",[]))
        if report["players"]:
            store_team(teams, team, report)
            filled.add(codes_for(team)[0])
        elif not any(teams.get(code,{}).get("players") for code in codes_for(team)):
            store_team(teams, team, report)
    return len(filled)

def candidate_codes(team):
    codes=[]
    for code in (str(team or "").upper(),)+tuple(codes_for(team)):
        if code and code not in codes: codes.append(code)
    return tuple(codes)

def fallback_team(data, team, load_team):
    """Fill one club from per-team endpoints when the league feed has no players.

    An HTTP 200 body of {} is status "empty". A failed request, with no empty
    body to inspect, is status "unavailable". Neither is "retrieved".
    """
    teams=data.setdefault("teams",{})
    if any(isinstance(teams.get(code), dict) and teams[code].get("players") for code in codes_for(team)):
        return "skipped"
    saw_empty=False
    for code in candidate_codes(team):
        try:
            raw=load_team(code)
        except Exception:
            continue
        report=report_from_payload(raw)
        if report["players"]:
            store_team(teams, team, report)
            return "retrieved"
        saw_empty=True
    if saw_empty:
        store_team(teams, team, {"status":"empty","players":[]})
        return "empty"
    if not any(code in teams for code in codes_for(team)):
        store_team(teams, team, {"status":"unavailable","players":[]})
    return "unavailable"

def league_has_players(node):
    """True when the raw league payload contains an athlete status row."""
    if isinstance(node, dict):
        athlete=node.get("athlete")
        if isinstance(athlete, dict) and (athlete.get("displayName") or athlete.get("fullName")) and ("status" in node or "type" in node):
            return True
        return any(league_has_players(value) for value in node.values())
    if isinstance(node, list):
        return any(league_has_players(value) for value in node)
    return False

def output_all_empty(data):
    teams=data.get("teams") if isinstance(data, dict) else None
    if not isinstance(teams, dict) or not teams: return True
    return not any(isinstance(report, dict) and report.get("players") for report in teams.values())

def assert_publishable(league, data):
    if league_has_players(league) and output_all_empty(data):
        raise InjuryPublishError("ESPN league injury feed contains players, but every team in the parsed output is empty.")

def teams_with_players(data):
    return sum(1 for team in TEAMS if any(data["teams"].get(code,{}).get("players") for code in codes_for(team)))

def main():
    data={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"source":"ESPN team injury reports","model_adjusted":False,"teams":{}}
    league=None
    try:
        req=urllib.request.Request("https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries",headers={"User-Agent":"Mozilla/5.0 FOURTHDOWN","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=15) as response:
            league=json.load(response)
    except Exception as exc:
        print(f"WARNING: ESPN league injury feed was not retrieved: {exc}")
    if league is not None:
        apply_league_feed(data, league)
    for team in TEAMS:
        fallback_team(data, team, load)
    # Scoped official-report fallback for the 2026 Week 7 Monday matchup.
    # Do not carry this historical snapshot into later games/weeks.
    today=datetime.now(timezone.utc).date()
    if datetime(2026,10,24,tzinfo=timezone.utc).date() <= today <= datetime(2026,10,27,tzinfo=timezone.utc).date():
        verified=Path("data/verified-week7-injuries.json")
        if verified.exists():
            snapshot=json.loads(verified.read_text(encoding="utf-8"))
            for team, rows in snapshot.get("teams",{}).items():
                current=lookup_report(data["teams"], team)
                players=list(current.get("players",[]))
                for name,position,status in rows:
                    # Official game designation takes precedence over generic ESPN labels.
                    players=[r for r in players if r.get("player","").casefold()!=name.casefold()]
                    players.append({"player":name,"position":position,"status":status,"detail":"Official game designation"})
                store_team(data["teams"], team, {"status":"retrieved","players":players,"source":snapshot["source"],"source_url":snapshot["source_url"]})
            data["official_snapshot"]={"season":2026,"week":7,"teams":["DAL","PHI"],"source_url":snapshot["source_url"]}
    if league is not None:
        try:
            assert_publishable(league, data)
        except InjuryPublishError as exc:
            raise SystemExit(f"REFUSING TO PUBLISH injuries.json: {exc}") from exc
    ok=teams_with_players(data)
    if not ok:
        print("WARNING: No current injury feeds available; publishing explicit empty or unavailable statuses.")
    Path("data").mkdir(exist_ok=True)
    Path("data/injuries.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print(f"Fetched {ok}/{len(TEAMS)} team injury reports")
if __name__=="__main__": main()
