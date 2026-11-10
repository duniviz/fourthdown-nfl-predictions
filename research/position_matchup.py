"""Leakage-safe position-specific opponent matchup challenger, 2024/2025.

Prior-week only defensive allowed production, grouped by RB/WR/TE/QB.
Compare on identical observations against workload baseline and existing
unsegmented opponent matchup. Research only; never modifies live forecasts.
"""
import json, math
from collections import defaultdict
from pathlib import Path
import nflreadpy as nfl
from research.walkforward_2024_2025 import MARKETS, num, run

POSITIONS={'QB','RB','WR','TE'}
def position_matchups(players, base_records):
    # Reconstruct matching predictions in chronological order, preserving
    # the existing research model's baseline/workload math.
    by_week=defaultdict(list)
    for r in players:
        if int(r.get('season',0)) in (2024,2025) and str(r.get('season_type','REG'))=='REG':
            by_week[(int(r['season']),int(r['week']))].append(r)
    history=defaultdict(list)
    defense=defaultdict(list)
    outputs=[]
    for (season,week),current in sorted(by_week.items()):
        # Freeze defensive records before ingesting any games this week.
        for r in current:
            pid=str(r.get('player_id') or '')
            team=str(r.get('recent_team') or r.get('team') or '')
            opp=str(r.get('opponent_team') or '')
            pos=str(r.get('position') or '').upper()
            if not pid or not team or not opp or pos not in POSITIONS:continue
            prior=history[(season,pid)]
            if len(prior)<3:continue
            for market,volume in MARKETS.items():
                if pos=='QB' and market not in ('passing_yards',):continue
                if pos=='RB' and market not in ('rushing_yards','receiving_yards','receptions'):continue
                if pos in ('WR','TE') and market not in ('receiving_yards','receptions'):continue
                h=prior[-8:]
                weights=[.86**(len(h)-1-i) for i in range(len(h))]
                baseline=sum(w*num(x.get(market)) for w,x in zip(weights,h))/sum(weights)
                vols=[num(x.get(volume)) for x in prior[-5:]]
                if not sum(vols):continue
                recent=sum(vols[-3:])/min(3,len(vols))
                mean=sum(vols)/len(vols)
                workload=baseline*max(.65,min(1.35,(.7*recent+.3*mean)/max(1,mean)))
                # Team-week totals by position, not player appearance averages.
                opponent=defense[(season,opp,pos,market)]
                league=[v for (s,t,p,m),vs in defense.items()
                        if s==season and p==pos and m==market for v in vs[-5:]]
                if len(opponent)>=3 and len(league)>=16:
                    neutral=sum(league)/len(league)
                    observed=sum(opponent[-5:])/len(opponent[-5:])
                    factor=(observed+5*neutral)/max(.1,6*neutral)
                    factor=max(.90,min(1.10,factor))
                else:factor=1.
                outputs.append({'season':season,'week':week,'market':market,'position':pos,
                                'actual':num(r.get(market)),'workload':workload,
                                'position_matchup':workload*factor})
        week_allowed=defaultdict(float)
        for r in current:
            pid=str(r.get('player_id') or '')
            opp=str(r.get('opponent_team') or '')
            pos=str(r.get('position') or '').upper()
            if pid:
                history[(season,pid)].append(r)
            if opp and pos in POSITIONS:
                for market in MARKETS:
                    week_allowed[(opp,pos,market)]+=num(r.get(market))
        for (opp,pos,market),value in week_allowed.items():
            defense[(season,opp,pos,market)].append(value)
    return outputs

def main():
    players=nfl.load_player_stats([2024,2025]).to_dicts()
    rows=position_matchups(players,[])
    if not rows:raise RuntimeError('No eligible position matchup records')
    report={}
    for season in (2024,2025):
        for market in MARKETS:
            for pos in POSITIONS:
                subset=[r for r in rows if r['season']==season and r['market']==market and r['position']==pos]
                if not subset:continue
                report[f'{season}:{pos}:{market}']={
                    'n':len(subset),
                    'workload_mae':round(sum(abs(r['workload']-r['actual']) for r in subset)/len(subset),3),
                    'position_matchup_mae':round(sum(abs(r['position_matchup']-r['actual']) for r in subset)/len(subset),3)}
    out=Path('research/position-matchup');out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps({'research_only':True,'results':report},indent=2)+'\n')
    lines=['# Position-specific defensive matchup backtest','','2024 and 2025, frozen prior-week defense production. Research only; no live model changes.','','| Season | Position | Market | N | Workload MAE | Position-matchup MAE |','|---|---|---|---:|---:|---:|']
    for key,v in report.items():
        season,pos,market=key.split(':')
        lines.append(f"| {season} | {pos} | {market} | {v['n']} | {v['workload_mae']} | {v['position_matchup_mae']} |")
    lines+=['','Defensive allowances are team-week totals by position, not league defensive rank. Shrunk toward the league average and capped at ±10%. No current-week results used.','This compares research proxies, not exact production replay or DraftKings profitability.']
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))
if __name__=='__main__':main()
