"""Weekly self-learning corrections with chronological validation and fail-closed promotion.

Uses only archived first-published predictions and completed prior weeks.
Adjusts current forecasts only when a market has demonstrated lower walk-forward MAE.
"""
import json
from collections import defaultdict
from pathlib import Path

MIN_TRAIN=16
MIN_TEST=12
PRIOR=50.0
MAX_CORRECTION=3.0

def fit(history):
    return max(-MAX_CORRECTION,min(MAX_CORRECTION,sum(history)/(len(history)+PRIOR))) if len(history)>=MIN_TRAIN else 0.0

def evaluate(archive,schedules,target_season,target_week):
    completed={str(g['game_id']):g for g in schedules if g.get('home_score') is not None and g.get('away_score') is not None}
    grouped=defaultdict(list)
    seen=set()
    for g in archive:
        gid=str(g.get('game_id',''))
        if gid in seen or gid not in completed:continue
        seen.add(gid)
        try:
            season,week=int(g['season']),int(g['week'])
            if (season,week)>=(target_season,target_week):continue
            actual=completed[gid]
            margin=float(actual['home_score'])-float(actual['away_score'])
            total=float(actual['home_score'])+float(actual['away_score'])
            grouped[(season,week)].append((float(g['projected_margin_home']),float(g['projected_total']),margin,total))
        except (ValueError,KeyError,TypeError):continue
    histories={'margin':[],'total':[]}
    trials={'margin':[],'total':[]}
    for key in sorted(grouped):
        corrections={name:fit(histories[name]) for name in histories}
        for pm,pt,am,at in grouped[key]:
            for name,pred,actual in [('margin',pm,am),('total',pt,at)]:
                if len(histories[name])>=MIN_TRAIN:
                    trials[name].append((abs(actual-pred),abs(actual-pred-corrections[name])))
        for pm,pt,am,at in grouped[key]:
            histories['margin'].append(am-pm)
            histories['total'].append(at-pt)
    decision={}
    for name in ('margin','total'):
        comparisons=trials[name]
        base=sum(x for x,_ in comparisons)/len(comparisons) if comparisons else None
        learned=sum(y for _,y in comparisons)/len(comparisons) if comparisons else None
        enabled=(len(comparisons)>=MIN_TEST and learned is not None and learned+0.05<base)
        decision[name]={'enabled':enabled,'adjustment':round(fit(histories[name]),3) if enabled else 0.,
                        'walkforward_games':len(comparisons),'baseline_mae':round(base,3) if base is not None else None,
                        'learner_mae':round(learned,3) if learned is not None else None}
    return decision

def main():
    import nflreadpy as nfl
    live_path=Path('data/live-v2.json')
    live=json.loads(live_path.read_text())
    season,week=int(live['season']),int(live['week'])
    archive=json.loads(Path('data/v2-history.json').read_text()).get('games',[])
    seasons=sorted({int(g['season']) for g in archive if int(g['season'])<=season})
    schedules=[g for s in seasons for g in nfl.load_schedules([s]).to_dicts()]
    decision=evaluate(archive,schedules,season,week)
    for game in live['games']:
        if game.get('weekly_learning'):continue
        margin=float(game['projected_margin_home'])+decision['margin']['adjustment']
        total=max(1.,float(game['projected_total'])+decision['total']['adjustment'])
        home=max(0.,(total+margin)/2);away=max(0.,(total-margin)/2)
        game.update(projected_home_score=round(home,1),projected_away_score=round(away,1),
                    projected_margin_home=round(home-away,2),projected_total=round(home+away,2),
                    predicted_winner=game['home'] if home>away else game['away'],
                    weekly_learning={'version':'bias-v1','margin_adjustment':decision['margin']['adjustment'],
                                     'total_adjustment':decision['total']['adjustment']})
    live['weekly_learning']={'method':'chronological_shrunk_residual','validation':decision,
                             'note':'Validated margin and total bias corrections only; ATS/total probabilities are not calibrated.'}
    live_path.write_text(json.dumps(live,indent=2)+'\n')
    Path('data/game-learning-status.json').write_text(json.dumps({'season':season,'week':week,'validation':decision},indent=2)+'\n')
    print(json.dumps(decision,indent=2))
if __name__=='__main__':main()
