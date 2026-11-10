"""Evaluate weekly online bias learning using only earlier completed games.

Research-only. No change to production model, recommendations, or calibration.
"""
import json
from collections import defaultdict
from pathlib import Path

MIN_HISTORY=40
SHRINK=80
def evaluate(rows):
    weeks=defaultdict(list)
    for r in rows:
        try:
            game=str(r['game_id'])
            season,week=int(game[:4]),int(game.split('_')[1])
            actual=float(r['actual']);pred=float(r['projection'])
            stat=str(r['stat_key'])
        except (KeyError,TypeError,ValueError,IndexError):continue
        weeks[(season,week)].append((stat,pred,actual))
    history=defaultdict(list)
    report=[]
    for season,week in sorted(weeks):
        # Freeze adjustments before any result from this week is ingested.
        frozen={}
        for stat,_,_ in weeks[(season,week)]:
            past=history[stat]
            frozen[stat]=(sum(past)/len(past))*len(past)/(len(past)+SHRINK) if len(past)>=MIN_HISTORY else 0
        for stat,pred,actual in weeks[(season,week)]:
            corrected=pred+frozen[stat]
            report.append({'season':season,'week':week,'market':stat,'baseline_error':abs(pred-actual),
                           'learner_error':abs(corrected-actual),'learned_bias':frozen[stat]})
        for stat,pred,actual in weeks[(season,week)]:
            history[stat].append(actual-pred)
    return report

def main():
    rows=json.loads(Path('data/player-results.json').read_text()).get('rows',[])
    result=evaluate(rows)
    if not result: raise RuntimeError('No graded archived forecasts')
    markets=defaultdict(list)
    for r in result: markets[r['market']].append(r)
    summary={}
    for name,rs in sorted(markets.items()):
        n=len(rs);base=sum(x['baseline_error'] for x in rs)/n;learn=sum(x['learner_error'] for x in rs)/n
        active=sum(bool(x['learned_bias']) for x in rs)
        summary[name]={'n':n,'adjusted_forecasts':active,'baseline_mae':round(base,3),
                       'online_learner_mae':round(learn,3),'mae_delta':round(learn-base,3),
                       'improved':learn<base}
    out=Path('research/weekly-learning');out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps({'research_only':True,'markets':summary},indent=2)+'\n')
    lines=['# Weekly learning audit','','Research only — live model unchanged. Adjustments for each week use only results from prior weeks.','', '| Market | Forecasts | Learned-adjusted | Baseline MAE | Learner MAE | Delta |','|---|---:|---:|---:|---:|---:|']
    for name,r in summary.items():
        lines.append(f"| {name} | {r['n']} | {r['adjusted_forecasts']} | {r['baseline_mae']:.2f} | {r['online_learner_mae']:.2f} | {r['mae_delta']:+.2f} |")
    lines+=['','Negative delta is improvement. This tests bias correction only, not a full weekly retrained machine-learning model.','Archived forecasts must be genuine pregame snapshots. No automatic promotion.']
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))
if __name__=='__main__':main()
