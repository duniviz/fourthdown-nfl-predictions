"""Choose the best *tested* player configuration per market; fail closed on game picks.

This report is advisory. Nothing here alters player-ml-runtime.json,
game-ml-runtime.json, live forecasts, official pregame locks, or cards.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

PLAYER_MARKETS=("passing_yards","rushing_yards","receiving_yards")
GAME_MARKETS=("winner","ats","ou")
MIN_PLAYER_ROWS=100
MIN_PLAYER_WEEKS=6
MIN_GAME_PAIRED=100
MIN_GAME_WEEKS=6
MIN_GAME_PICK_ROWS=40

def choose_player(market,report):
    samples=int(report.get("holdout_rows",0))
    weeks=int(report.get("holdout_weeks",0))
    coverage=report.get("source_coverage",{})
    available={}
    for name,model in report.get("models",{}).items():
        if model.get("status")!="evaluated" or int(model.get("samples",0))!=samples:
            continue
        # A dataset that was not observed cannot win a feature experiment.
        if name=="ngs" and not coverage.get("ngs"):continue
        if name=="snap_counts" and not coverage.get("snap"):continue
        if name=="pfr_advanced" and not coverage.get("pfr"):continue
        if name=="combined" and not (coverage.get("ngs") and coverage.get("snap")):continue
        try:mae=float(model["challenger_mae"])
        except (KeyError,TypeError,ValueError):continue
        if mae>=0 and mae<1e6:available[name]=mae
    if samples<MIN_PLAYER_ROWS or weeks<MIN_PLAYER_WEEKS or not available:
        return {"research_winner":None,"reason":"insufficient_matched_holdout_or_source_coverage",
                "samples":samples,"weeks":weeks,"card_model_changed":False}
    # Prefer fewer sources in a near-tie; exclude missing PFR from "combined" provenance.
    order=("baseline_features","ngs","snap_counts","combined","pfr_advanced")
    winner=min(available,key=lambda x:(available[x],order.index(x)))
    gain=report["models"][winner].get("improvement_pct")
    return {"research_winner":winner,"heldout_mae":round(available[winner],3),
            "baseline_mae":report["models"][winner].get("baseline_mae"),
            "relative_improvement_pct":gain,"samples":samples,"weeks":weeks,
            "source_coverage":coverage,"card_model_changed":False,
            "notes":"Retrospective weekly walk-forward result, not matched frozen live evidence"}

def choose_games(runtime):
    decisions=runtime.get("decisions",{})
    specs={"winner":("game_margin_home","winner"),
           "ats":("game_margin_home","ats"),
           "ou":("game_total","ou")}
    result={}
    for market,(model,key) in specs.items():
        decision=decisions.get(model,{})
        pick=decision.get("pick_checks",{}).get(key,{})
        paired=int(decision.get("paired",0) or 0)
        weeks=int(decision.get("weeks",0) or 0)
        observed=int(pick.get("games",0) or 0)
        base_hits=int(pick.get("baseline_hits",0) or 0)
        candidate_hits=int(pick.get("candidate_hits",0) or 0)
        sufficient=paired>=MIN_GAME_PAIRED and weeks>=MIN_GAME_WEEKS and observed>=MIN_GAME_PICK_ROWS
        # The game trainer controls actual promotion; respect its active flags.
        active=decision.get("active") is True
        result[market]={"research_winner":"game_ml" if sufficient and candidate_hits>base_hits else "baseline",
            "paired_games":paired,"weeks":weeks,"graded_picks":observed,
            "baseline_hits":base_hits,"ml_hits":candidate_hits,
            "accuracy_baseline_pct":round(base_hits/observed*100,2) if observed else None,
            "accuracy_ml_pct":round(candidate_hits/observed*100,2) if observed else None,
            "evidence_status":"sufficient" if sufficient else "insufficient_paired_game_evidence",
            "active_in_production":active,"card_model_changed":False}
    return result

def select(player_report,game_runtime):
    return {"generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "research_only":True,"production_changed":False,
      "player":{market:choose_player(market,player_report.get("markets",{}).get(market,{}))
                for market in PLAYER_MARKETS},
      "game":choose_games(game_runtime),
      "explanation":"Research winners are not new live ML card projections. Exact live as-of feature parity and frozen evidence are required before activation."}

def main():
    players=json.loads(Path("data/research-free-nfl-features.json").read_text())
    game=json.loads(Path("data/game-ml-runtime.json").read_text())
    out=select(players,game)
    dest=Path("data/market-ml-research-selection.json")
    dest.write_text(json.dumps(out,indent=2)+"\n")
    for market,result in out["player"].items():print("PLAYER",market,result["research_winner"],result["samples"],"rows")
    for market,result in out["game"].items():print("GAME",market,result["research_winner"],result["evidence_status"])
if __name__=="__main__":main()
