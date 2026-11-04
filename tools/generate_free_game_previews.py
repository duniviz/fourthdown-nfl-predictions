#!/usr/bin/env python3
"""Free, evidence-grounded matchup previews. No external AI service or API charges."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORECAST = ROOT / "data/live-v2.json"
OUTPUT = ROOT / "data/ai-game-previews.json"

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
    for game in forecasts.get("games",[]):
        gid=game.get("game_id")
        if not gid or not game.get("kickoff_utc") or not game.get("analysis"):
            continue
        kickoff=datetime.fromisoformat(game["kickoff_utc"].replace("Z","+00:00"))
        prior=old.get(gid)
        # Preserve existing editorial writing when projections and kickoff have not changed.
        signature=json.dumps({"kickoff":game["kickoff_utc"],"home":game["home"],
          "away":game["away"],"scores":[game["projected_home_score"],game["projected_away_score"]],
          "analysis":game["analysis"]},sort_keys=True)
        if prior and (prior.get("free_evidence_signature")==signature or
                      (not prior.get("free_evidence_signature") and prior.get("kickoff_utc")==game["kickoff_utc"])):
            updated[gid]=prior
            continue
        if kickoff <= now:
            if prior: updated[gid]=prior
            continue
        updated[gid]={**describe(game),"generated_at_utc":now.isoformat(),
            "kickoff_utc":game["kickoff_utc"],"free_evidence_signature":signature,
            "source":"Free evidence-based model commentary (not generative AI)"}
    result={"schema_version":1,"games":updated}
    serialized=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
    if not OUTPUT.exists() or OUTPUT.read_text()!=serialized:
        OUTPUT.write_text(serialized)
    print(f"Free previews available: {len(updated)} for forecast week {forecasts.get('week')}")
    if not updated: raise SystemExit("No previews generated for current forecast slate")

if __name__=="__main__":
    main()
