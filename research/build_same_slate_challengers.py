#!/usr/bin/env python3
"""Build chronological same-slate bias challengers from genuine pregame archives.

No reconstructed timestamps or postgame inputs. Prior-week residuals only.
These are simple challenger families, not claims of full V3 equivalence.
"""
import argparse,collections,datetime as dt,json,math,pathlib
def stamp(s):
    try:return dt.datetime.fromisoformat(str(s).replace("Z","+00:00")).astimezone(dt.timezone.utc)
    except (ValueError,TypeError):return None
def number(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):return None
def generate(rows):
    weeks=collections.defaultdict(list); rejected=collections.Counter()
    for r in rows:
        try:
            game=str(r["game_id"]); season,week=map(int,game.split("_")[:2])
            kickoff=stamp(r.get("kickoff_utc")); predtime=stamp(r.get("predicted_at_utc"))
            actual=number(r.get("actual")); projection=number(r.get("projection"))
            if not kickoff or not predtime or predtime>=kickoff or actual is None or projection is None or not r.get("player_id") or not r.get("stat_key") or r.get("dnp") or r.get("played") is False:
                rejected["unverified_or_missing_pregame"]+=1;continue
            weeks[(season,week)].append((r,projection,actual))
        except (ValueError,KeyError,TypeError):rejected["invalid"]+=1
    history=collections.defaultdict(list); out=[]
    for key in sorted(weeks):
        frozen={}
        for r,p,a in weeks[key]:
            market=str(r["stat_key"]); prior=history[market]
            if market not in frozen:
                frozen[market]={
                    "live":0.0,
                    "bias_shrink_40":sum(prior)/len(prior)*len(prior)/(len(prior)+40) if len(prior)>=30 else 0.0,
                    "bias_shrink_80":sum(prior)/len(prior)*len(prior)/(len(prior)+80) if len(prior)>=30 else 0.0,
                    "recent_bias_40":sum(prior[-40:])/len(prior[-40:])*.5 if len(prior)>=30 else 0.0
                }
        for r,p,a in weeks[key]:
            for model,offset in frozen[str(r["stat_key"])].items():
                out.append({k:r.get(k) for k in ("game_id","player_id","stat_key","kickoff_utc","predicted_at_utc","dk_line","team","player")}|{"model":model,"projection":round(max(0,p+offset),4),"actual":a})
        for r,p,a in weeks[key]:
            history[str(r["stat_key"])].append(a-p)
    return {"rows":out,"rejected":dict(rejected),"note":"Historical chronological bias challengers only; each week frozen before its outcomes"}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",default="data/player-results.json");ap.add_argument("--output",default="research/same-slate/pregame-forecasts.json")
    args=ap.parse_args();src=json.loads(pathlib.Path(args.input).read_text());data=generate(src.get("rows",src) if isinstance(src,dict) else src)
    if not data["rows"]:raise SystemExit("No timestamp-verified pregame rows; refusing to fabricate a same-slate comparison")
    dest=pathlib.Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(data,indent=2)+"\n")
    print("Generated",len(data["rows"]),"same-slate forecasts")
if __name__=="__main__":main()
