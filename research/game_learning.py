"""Research-only chronological game score, spread and total learning audit.

Reads archived pregame V2 snapshots. Updates bias only after the entire week.
Does not use market lines unless they were archived with the prediction.
"""
import json, math
from collections import defaultdict
from pathlib import Path

MIN_GAMES=12
PRIOR=40
def learn(archive,schedules):
    completed={str(x['game_id']):x for x in schedules if x.get('home_score') is not None and x.get('away_score') is not None}
    by_week=defaultdict(list)
    for r in archive:
        gid=str(r.get('game_id',''))
        if gid not in completed: continue
        try: key=(int(r['season']),int(r['week']))
        except (ValueError,KeyError,TypeError):continue
        by_week[key].append(r)
    past_margin=[];past_total=[];out=[]
    for season,week in sorted(by_week):
        # Freeze parameters for the entire week before grading any game.
        adj_m=(sum(past_margin)/(len(past_margin)+PRIOR)) if len(past_margin)>=MIN_GAMES else 0.
        adj_t=(sum(past_total)/(len(past_total)+PRIOR)) if len(past_total)>=MIN_GAMES else 0.
        residuals=[]
        for r in by_week[(season,week)]:
            actual=completed[str(r['game_id'])]
            home=float(actual['home_score']);away=float(actual['away_score'])
            pm=float(r['projected_margin_home']);pt=float(r['projected_total'])
            margin=home-away;total=home+away
            # Spread and total are assessed as numeric margins/totals; true ATS grading
            # requires pregame archived lines, not retrospective market prices.
            out.append({'season':season,'week':week,'game_id':r['game_id'],
                        'margin_error_baseline':abs(pm-margin),'margin_error_learned':abs(pm+adj_m-margin),
                        'total_error_baseline':abs(pt-total),'total_error_learned':abs(pt+adj_t-total),
                        'home_score_error_baseline':abs((pt+pm)/2-home),
                        'away_score_error_baseline':abs((pt-pm)/2-away),
                        'home_score_error_learned':abs((pt+adj_t+pm+adj_m)/2-home),
                        'away_score_error_learned':abs((pt+adj_t-pm-adj_m)/2-away),
                        'winner_baseline':(pm>0)==(margin>0),
                        'winner_learned':(pm+adj_m>0)==(margin>0),
                        'margin_bias':adj_m,'total_bias':adj_t})
            residuals.append((margin-pm,total-pt))
        past_margin.extend(x for x,_ in residuals)
        past_total.extend(y for _,y in residuals)
    return out

def summary(rows):
    if not rows:return {'status':'no_graded_games'}
    keys=['margin_error','total_error','home_score_error','away_score_error']
    metrics={}
    for key in keys:
        metrics[key]={'baseline_mae':round(sum(x[key+'_baseline'] for x in rows)/len(rows),3),
                      'learned_mae':round(sum(x[key+'_learned'] for x in rows)/len(rows),3)}
    metrics['winner_accuracy']={k:round(sum(x['winner_'+k] for x in rows)/len(rows),4) for k in ('baseline','learned')}
    return {'games':len(rows),'metrics':metrics,'weeks':len(set((r['season'],r['week']) for r in rows))}

def main():
    import nflreadpy as nfl
    archive=json.loads(Path('data/v2-history.json').read_text()).get('games',[])
    seasons=sorted({int(r['season']) for r in archive})
    schedules=[g for s in seasons for g in nfl.load_schedules([s]).to_dicts()]
    graded=learn(archive,schedules);results=summary(graded)
    out=Path('research/game-learning');out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps({'research_only':True,'results':results},indent=2)+'\n')
    lines=['# Weekly game score / spread / total learning audit','','Research only. Live model unchanged. Only archived pregame projections are graded.','',f"Games graded: {results.get('games',0)}",f"Weeks graded: {results.get('weeks',0)}",'']
    if 'metrics' in results:
        lines+=['| Metric | Baseline | Prior-week bias learner |','|---|---:|---:|']
        for name,m in results['metrics'].items():
            a=m.get('baseline_mae',m.get('baseline'));b=m.get('learned_mae',m.get('learned'))
            lines.append(f'| {name.replace("_"," ")} | {a} | {b} |')
    lines+=['','## Limitations','','- Archived V2 snapshots only; this is not a 2024–2025 historical reconstruction.','- A simple shrunk residual learner is tested, not full model retraining.','- ATS and Over/Under bet hit rates require timestamped pregame sportsbook lines and odds. No retrospective lines are substituted.','- Score/margin/total errors are evaluated on the same completed games.','- Changes are not promoted to live predictions automatically.']
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))
if __name__=='__main__':main()
