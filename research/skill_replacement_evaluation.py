"""Walk-forward research of skill-player workload changes, not starter labels.

Cohort: the team's previous-three-game volume leader does not appear in the
next game; evaluate other players of that position with prior same-team games.
Leader absence is known retrospectively and is only a proxy for replacement.
Inputs to both estimates use strictly previous weeks; outcome selection never
uses target opportunities. This is NOT a replay of published projections.
"""
import argparse, csv, json, math
from collections import defaultdict
from live.player_research import project_yards
from research.replacement_starter_backtest import estimate

SPECS={'RB':('carries','rushing_yards'), 'WR':('targets','receiving_yards'), 'TE':('targets','te_receiving_yards')}

def evaluate(rows):
    grouped=defaultdict(list)
    for r in rows:
        if r.get('season_type')=='REG' and r.get('player_id') and r.get('team') and r.get('position') in SPECS:
            grouped[(int(r['season']),int(r['week']))].append(r)
    prior_player=defaultdict(list)
    prior_team=defaultdict(lambda:defaultdict(list))
    scored=defaultdict(list)
    for (season,week), current in sorted(grouped.items()):
        games=defaultdict(list)
        for r in current: games[(r['team'],r['position'])].append(r)
        for (team,pos), active in games.items():
            volume,market=SPECS[pos]
            prior=prior_team[(season,team,pos)]
            weeks=sorted(prior)[-3:]
            if len(weeks)<3: continue
            totals=defaultdict(float)
            for w in weeks:
                for r in prior[w]: totals[r['player_id']]+=max(0,float(r.get(volume) or 0))
            if not totals: continue
            leader=max(totals,key=totals.get)
            if totals[leader]<=0 or any(r['player_id']==leader for r in active): continue
            for r in active:
                pid=r['player_id']
                history=prior_player[pid]
                same_team=[h for h in history if int(h['season'])==season and h.get('team')==team and h.get('position')==pos]
                if not same_team: continue
                prediction=estimate(history,market)
                if prediction is None: continue
                stat='receiving_yards' if pos=='TE' else market
                baseline=project_yards(same_team,stat,volume)[0]
                actual=float(r.get(stat) or 0)
                scored[(season,pos)].append((baseline-actual,prediction-actual))
        for r in current:
            prior_player[r['player_id']].append(r)
            prior_team[(season,r['team'],r['position'])][week].append(r)
    def summary(values):
        if not values: return {'games':0}
        def measure(i): return {'mae':round(sum(abs(x[i]) for x in values)/len(values),2),'rmse':round(math.sqrt(sum(x[i]**2 for x in values)/len(values)),2)}
        return {'games':len(values),'current_component':measure(0),'candidate':measure(1)}
    return {'status':'research_only', 'by_season_position':{f'{y}_{p}':summary(v) for (y,p),v in sorted(scored.items())},
            'by_position':{p:summary([e for (y,pos),values in scored.items() if pos==p for e in values]) for p in SPECS},
            'limitations':['Leader absent is retrospective, not confirmation of a replacement starter.', 'Target sample includes only players who appeared in the game.', 'Comparator is a yardage component, not complete published production.', 'History requires three prior meaningful opportunities; no same-week inputs.']}

def main():
    p=argparse.ArgumentParser(); p.add_argument('stats');p.add_argument('--output');a=p.parse_args()
    with open(a.stats,newline='') as f: result=evaluate(list(csv.DictReader(f)))
    report=json.dumps(result,indent=2)+'\n'
    if a.output:
        with open(a.output,'w') as f: f.write(report)
    print(report)
if __name__=='__main__': main()
