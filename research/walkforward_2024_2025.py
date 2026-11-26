"""Chronological 2024-25 player-prop research; production model is untouched."""
import json, math
from collections import defaultdict
from pathlib import Path
import nflreadpy as nfl

MARKETS={'passing_yards':'attempts','rushing_yards':'carries','receiving_yards':'targets','receptions':'targets'}
def num(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else 0.
    except (TypeError,ValueError): return 0.

def run(players,snaps,injuries):
    grouped=defaultdict(list)
    for r in players:
        if int(r.get('season',0)) in (2024,2025) and r.get('season_type','REG')=='REG':
            grouped[(int(r['season']),int(r['week']))].append(r)
    snap_index={}
    for r in snaps:
        try: snap_index[(int(r['season']),int(r['week']),str(r['player_id']))]=num(r.get('offense_pct'))
        except (ValueError,TypeError,KeyError): continue
    injury_index=defaultdict(list)
    for r in injuries:
        try: injury_index[(int(r['season']),int(r['week']),str(r.get('gsis_id') or r.get('player_id') or ''))].append(r)
        except (ValueError,TypeError,KeyError): continue
    history=defaultdict(list); allowed=defaultdict(list); prev_injury=defaultdict(bool); output=[]
    for season,week in sorted(grouped):
        current=grouped[(season,week)]
        # Forecast the entire week before ingesting any of its outcomes.
        for r in current:
            pid=str(r.get('player_id') or '')
            team=str(r.get('recent_team') or r.get('team') or '')
            opp=str(r.get('opponent_team') or '')
            if not pid or not team or not opp: continue
            prior=history[(season,pid)]
            if len(prior)<3: continue
            for market,volume in MARKETS.items():
                h=prior[-8:]
                weights=[.86**(len(h)-1-i) for i in range(len(h))]
                baseline=sum(w*num(x.get(market)) for w,x in zip(weights,h))/sum(weights)
                vols=[num(x.get(volume)) for x in prior[-5:]]
                if sum(vols)==0: continue
                recent=sum(vols[-3:])/min(3,len(vols))
                mean=sum(vols)/len(vols)
                workload=baseline*max(.65,min(1.35,(.7*recent+.3*mean)/max(1,mean)))
                snap_hist=[x['snap'] for x in prior[-5:] if x.get('snap') is not None]
                if len(snap_hist)>=3:
                    before=sum(snap_hist[:-2])/len(snap_hist[:-2])
                    after=sum(snap_hist[-2:])/2
                    workload*=max(.8,min(1.2,after/max(.05,before)))
                # Only prior opponent defensive allowances; shrink small samples.
                opponent=allowed[(season,opp,market)]
                matchup=workload
                if len(opponent)>=3:
                    league=[v for (s,t,m),vs in allowed.items() if s==season and m==market for v in vs[-5:]]
                    if league:
                        neutral=sum(league)/len(league)
                        factor=(sum(opponent[-5:])/len(opponent[-5:])+5*neutral)/max(.1,6*neutral)
                        matchup*=max(.85,min(1.15,factor))
                # Only previous-week injury signal: never use revised current-week status.
                injury=matchup*(.90 if prev_injury[(season,pid)] else 1)
                output.append(dict(season=season,week=week,market=market,actual=num(r.get(market)),
                                   baseline=baseline,workload=workload,matchup=matchup,injury=injury))
        for r in current:
            pid=str(r.get('player_id') or '')
            team=str(r.get('recent_team') or r.get('team') or '')
            opp=str(r.get('opponent_team') or '')
            if not pid or not team or not opp: continue
            snap=snap_index.get((season,week,pid))
            if snap is not None and snap>1: snap/=100
            history[(season,pid)].append(dict(r,snap=snap))
            for market in MARKETS:
                allowed[(season,opp,market)].append(num(r.get(market)))
            reports=injury_index.get((season,week,pid),[])
            prev_injury[(season,pid)]=any(str(x.get('report_status') or x.get('game_status') or '').lower() in ('out','doubtful','questionable') for x in reports)
    return output

def main():
    players=nfl.load_player_stats([2024,2025]).to_dicts()
    snaps=nfl.load_snap_counts([2024,2025]).to_dicts()
    injuries=nfl.load_injuries([2024,2025]).to_dicts()
    records=run(players,snaps,injuries)
    if not records: raise RuntimeError('No eligible player rows: check historical data schema')
    result={}
    for season in (2024,2025):
        for market in MARKETS:
            subset=[r for r in records if r['season']==season and r['market']==market]
            if not subset: continue
            stats={'n':len(subset)}
            for model in ('baseline','workload','matchup','injury'):
                errors=[r[model]-r['actual'] for r in subset]
                stats[model]={'mae':round(sum(abs(e) for e in errors)/len(errors),3),
                              'rmse':round(math.sqrt(sum(e*e for e in errors)/len(errors)),3),
                              'bias':round(sum(errors)/len(errors),3)}
            result[f'{season}:{market}']=stats
    out=Path('research/backtest-2024-2025');out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps({'seasons':[2024,2025],'results':result,'live_model_changed':False},indent=2)+'\n')
    lines=['# FOURTHDOWN · 2024–2025 walk-forward backtest','','**Research only. Live model unchanged.**','','| Season | Market | N | Baseline MAE | Workload MAE | Matchup MAE | Injury-proxy MAE |','|---|---|---:|---:|---:|---:|---:|']
    for k,v in result.items():
        season,market=k.split(':')
        lines.append(f"| {season} | {market.replace('_',' ')} | {v['n']} | {v['baseline']['mae']:.2f} | {v['workload']['mae']:.2f} | {v['matchup']['mae']:.2f} | {v['injury']['mae']:.2f} |")
    lines+=['','## Method and caveats','','- Each entire week is predicted using only completed prior weeks; updates occur after predictions.','- Baseline is a recent-form research benchmark, **not an exact replay of the live production model**.','- Workload adds prior-week opportunity and snap trends; matchup adds prior opponent allowances, heavily shrunk.','- Injury variant uses a **previous-week injury-report proxy**, not verified same-week pre-kickoff injury status.','- All variants are compared on the same rows; no in-sample parameter tuning.','- Lower MAE and RMSE are better. Results do not establish betting profit or calibrated confidence.','- Require further independent validation before modifying production.','','Data: nflverse via nflreadpy.']
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    import html
    cells=[['Season','Market','N','Baseline MAE','Workload MAE','Matchup MAE','Injury-proxy MAE']]
    cells.extend([line.strip('|').split('|') for line in lines if line.startswith('| 202')])
    trs=''.join('<tr>'+''.join(('<th>' if i==0 else '<td>')+html.escape(str(x).strip())+('</th>' if i==0 else '</td>') for x in row)+'</tr>' for i,row in enumerate(cells))
    page='<!doctype html><html><meta name="viewport" content="width=device-width,initial-scale=1"><meta charset="utf-8"><title>FOURTHDOWN Backtest</title><style>body{font:16px system-ui;background:#0b1b2b;color:#edf5ff;padding:20px;max-width:1100px;margin:auto}h1,th{color:#c6ff39}.scroll{overflow-x:auto}table{border-collapse:collapse;min-width:720px}td,th{padding:12px;border-bottom:1px solid #496276;text-align:left}.note{background:#213b4e;padding:14px;border-radius:12px}</style><h1>FOURTHDOWN Historical Backtest</h1><p class="note">2024–2025 · Research only · Live model unchanged · Injury variant uses previous-week proxy.</p><div class="scroll"><table>'+trs+'</table></div><p>Lower MAE is better. See RESULTS.md for limitations and JSON for RMSE/bias.</p></html>'
    (out/'index.html').write_text(page)
    print('Compared',len(records),'paired player-market observations')
if __name__=='__main__': main()
