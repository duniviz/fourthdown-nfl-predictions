"""Retrospective replacement-role ML probe; never publish production predictions.

CSV inputs are nflverse weekly player stats and schedules. Evaluation selects
actual QB starters or games where a skill-position workload leader was absent
retrospectively. This is not a pregame availability test or a production replay.
Train only on earlier seasons, and use player features from prior weeks.
"""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
parser=argparse.ArgumentParser()
parser.add_argument('stats_csv'); parser.add_argument('schedule_csv')
args=parser.parse_args()
import csv,math
from collections import defaultdict
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from live.player_research import project_yards
rows=list(csv.DictReader(open(args.stats_csv)))
schedules=list(csv.DictReader(open(args.schedule_csv)))
qb_starters={}
for g in schedules:
 if g['game_type']=='REG':
  for side in ('home','away'):
   qb_starters[(int(g['season']),int(g['week']),g[side+'_team'])]=g[side+'_qb_id']
weekly=defaultdict(list)
for r in rows:
 if r['season_type']=='REG' and r['position'] in ('QB','RB','WR') and r['team'] and r['player_id']:
  weekly[(int(r['season']),int(r['week']))].append(r)
hist=defaultdict(list); teamhistory=defaultdict(lambda:defaultdict(list)); oldqb={}; data=defaultdict(list)
for (year,week),current in sorted(weekly.items()):
 groups=defaultdict(list)
 for r in current: groups[(r['team'],r['position'])].append(r)
 for (team,pos),players in groups.items():
  volume,metric={'QB':('attempts','passing_yards'),'RB':('carries','rushing_yards'),'WR':('targets','receiving_yards')}[pos]
  if pos=='QB':
   starter=qb_starters.get((year,week,team)); previous=oldqb.get((year,team)); oldqb[(year,team)]=starter
   if not previous or not starter or previous==starter: continue
   players=[p for p in players if p['player_id']==starter]
  else:
   previous_weeks=sorted(teamhistory[(year,team,pos)])[-3:]
   if len(previous_weeks)<3: continue
   totals=defaultdict(float)
   for w in previous_weeks:
    for p in teamhistory[(year,team,pos)][w]: totals[p['player_id']]+=float(p[volume] or 0)
   if not totals: continue
   leader=max(totals,key=totals.get)
   if totals[leader]<=0 or any(p['player_id']==leader for p in players):continue
  for p in players:
   prev=hist[p['player_id']]; curr=[h for h in prev if int(h['season'])==year and h['team']==team and h['position']==pos]
   if not curr:continue
   last=curr[-5:]; previous=[h for h in prev if h['position']==pos][-8:]
   mean=lambda x:sum(x)/len(x) if x else 0
   vals=lambda group,key:[float(v[key] or 0) for v in group]
   feat=[mean(vals(last,metric)),mean(vals(last,volume)),mean(vals(previous,metric)),mean(vals(previous,volume)),len(curr),week-int(curr[-1]['week'])]
   baseline=project_yards(curr,metric,volume)[0]
   data[pos].append((year,feat,baseline,float(p[metric] or 0)))
 for r in current:
  hist[r['player_id']].append(r);teamhistory[(year,r['team'],r['position'])][week].append(r)
for pos,records in data.items():
 for year in (2024,2025,2026):
  train=[r for r in records if r[0]<year];test=[r for r in records if r[0]==year]
  if len(train)<15 or not test: print(pos,year,'insufficient',len(train),len(test));continue
  model=make_pipeline(StandardScaler(),Ridge(alpha=100)); model.fit([r[1] for r in train],[r[3] for r in train]); pred=model.predict([r[1] for r in test]); n=len(test)
  mae=lambda es:round(sum(abs(e) for e in es)/n,2)
  rmse=lambda es:round(math.sqrt(sum(e*e for e in es)/n),2)
  b=[r[2]-r[3] for r in test]; m=[max(0,float(v))-r[3] for v,r in zip(pred,test)]
  print(pos,year,'train',len(train),'test',n,'baseline',mae(b),rmse(b),'ml',mae(m),rmse(m))
