"""Free NFL sources -> strictly prior-week research player features and ablation.

Does not edit production forecasts, runtime models, or frozen predictions.
No missing values are invented: unavailable observations are 0 with an explicit
missingness flag, and every report includes source-specific coverage.
"""
import argparse,csv,json,math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

MARKET_SOURCE={'passing_yards':'passing','rushing_yards':'rushing','receiving_yards':'receiving'}
NGS_METRICS={
 'passing':('avg_time_to_throw','avg_completed_air_yards','completion_percentage_above_expectation'),
 'receiving':('avg_separation','avg_cushion','avg_intended_air_yards'),
 'rushing':('efficiency','avg_time_to_los','rush_yards_over_expected_per_att'),
}
# PFR player IDs are not GSIS IDs. Never join by player names alone.
PFR_METRICS={
 'pass':('pressure_pct','bad_throw_pct','on_tgt_pct'),
 'rush':('yards_before_contact','yards_after_contact','broken_tackles'),
 'rec':('drops','drop_pct','yards_after_catch'),
}
MARKET_PFR={'passing_yards':'pass','rushing_yards':'rush','receiving_yards':'rec'}

def valid(v):
 try:
  x=float(v)
  return x if math.isfinite(x) else None
 except (TypeError,ValueError): return None

def week_key(row):
 try: return (int(row['season']),int(row['week']))
 except (KeyError,ValueError,TypeError): return None

def load_sources(nfl,seasons):
 datasets={}
 for market,kind in MARKET_SOURCE.items():
  for season in seasons:
   name=f'ngs_{kind}_{season}'
   try: datasets[name]=nfl.load_nextgen_stats([season],stat_type=kind).to_dicts()
   except (Exception) as exc:
    print('SOURCE_UNAVAILABLE',name,type(exc).__name__,str(exc)[:170])
 for season in seasons:
  for key,loader in [
   ('snap',lambda:nfl.load_snap_counts([season])),
   ('injuries',lambda:nfl.load_injuries([season])),
   ('depth',lambda:nfl.load_depth_charts([season])),
   ('players',lambda:nfl.load_players()),
  ]:
   name=f'{key}_{season}'
   if key=='players' and season!=seasons[0]:continue
   try:datasets[name]=loader().to_dicts()
   except (Exception) as exc:
    print('SOURCE_UNAVAILABLE',name,type(exc).__name__,str(exc)[:170])
  for kind in ('pass','rush','rec','def'):
   name=f'pfr_{kind}_{season}'
   try:datasets[name]=nfl.load_pfr_advstats([season],stat_type=kind,summary_level='week').to_dicts()
   except (Exception) as exc:
    print('SOURCE_UNAVAILABLE',name,type(exc).__name__,str(exc)[:170])
 return datasets

def assemble_index(datasets):
 pfr_id={}
 for name,rows in datasets.items():
  if not name.startswith('players_'):continue
  for r in rows:
   if r.get('gsis_id') and r.get('pfr_id'):pfr_id[str(r['gsis_id'])]=str(r['pfr_id'])
 series=defaultdict(list)
 coverage={}
 for source,rows in datasets.items():
  coverage[source]={'rows':len(rows),'eligible_rows':0}
  if source.startswith('ngs_'):
   kind=source.split('_')[1]
   metrics=NGS_METRICS[kind]
   for r in rows:
    k=week_key(r)
    if k is None or k[1]<1 or str(r.get('season_type','REG')).upper()!='REG':continue
    pid=r.get('player_gsis_id')
    if not pid:continue
    values=[valid(r.get(m)) for m in metrics]
    if not any(v is not None for v in values):continue
    series[(kind,str(pid))].append((k,values))
    coverage[source]['eligible_rows']+=1
  if source.startswith('snap_'):
   for r in rows:
    k=week_key(r)
    if k is None or k[1]<1 or str(r.get('game_type','REG')).upper()!='REG':continue
    pid=r.get('pfr_player_id')
    v=valid(r.get('offense_pct'))
    if pid and v is not None:
     series[('snap',str(pid))].append((k,[v]))
     coverage[source]['eligible_rows']+=1
  if source.startswith('pfr_'):
   kind=source.split('_')[1]
   if kind not in PFR_METRICS:continue
   for r in rows:
    k=week_key(r)
    if k is None or k[1]<1:continue
    pid=r.get('pfr_id') or r.get('pfr_player_id')
    vals=[valid(r.get(m)) for m in PFR_METRICS[kind]]
    if pid and any(x is not None for x in vals):
     series[(f'pfr_{kind}',str(pid))].append((k,vals))
     coverage[source]['eligible_rows']+=1
 # Source rows can have duplicate player/week entries; reject those periods.
 for key,items in list(series.items()):
  counts=defaultdict(int)
  for wk,_ in items:counts[wk]+=1
  series[key]=sorted((wk,vals) for wk,vals in items if counts[wk]==1)
 return series,pfr_id,coverage

def lagged_values(series,source,pid,target,n):
 """Only player observations from strictly older weeks; current week unavailable."""
 eligible=[v for k,v in series.get((source,str(pid)),[]) if k<target and
           k[0]>=target[0]-1 and (k[0]!=target[0] or k[1]>=target[1]-8)]
 eligible=eligible[-4:]
 out=[]
 for idx in range(n):
  xs=[v[idx] for v in eligible if v[idx] is not None]
  out.append(sum(xs)/len(xs) if xs else 0.0)
 return out, 1.0 if eligible else 0.0

def enriched_rows(base_rows,series,pfr_ids):
 out=[]
 for r in base_rows:
  market=r.get('market')
  if market not in MARKET_SOURCE:continue
  target=week_key(r)
  pid=r.get('player_id')
  if target is None or not pid:continue
  values=[valid(r.get(k)) for k in ('new','old','prior_games','recent_volume','recent_yards','team_volume','opponent_ratio','actual')]
  if any(v is None for v in values):continue
  ngs,ngs_seen=lagged_values(series,MARKET_SOURCE[market],pid,target,3)
  pfr=pfr_ids.get(str(pid))
  snap,snap_seen=lagged_values(series,'snap',pfr,target,1) if pfr else ([0.0],0.0)
  pfr_data,pfr_seen=lagged_values(series,'pfr_'+MARKET_PFR[market],pfr,target,3) if pfr else ([0.0]*3,0.0)
  base=[*values[:7],float(target[1])]
  out.append({'market':market,'key':target,'player_id':str(pid),'baseline':values[0],'actual':values[-1],
              'base':base,'ngs':ngs+[ngs_seen],'snap':snap+[snap_seen],
              'pfr':pfr_data+[pfr_seen]})
 return out

def assess(rows,min_train=100,min_test=30):
 report={}
 for market in MARKET_SOURCE:
  items=sorted([r for r in rows if r['market']==market],key=lambda r:(r['key'],r['player_id']))
  groups=sorted({r['key'] for r in items})
  holdouts=groups[-8:]
  outcomes=defaultdict(list)
  for key in holdouts:
   train=[r for r in items if r['key']<key]
   test=[r for r in items if r['key']==key]
   if len(train)<min_train or not test:continue
   for name,groups_selected in {'baseline_features':(),
      'ngs':('ngs',),'snap_counts':('snap',),'pfr_advanced':('pfr',),
      'combined':('ngs','snap','pfr')}.items():
    # Do not call a dataset a feature improvement when it was unavailable.
    if groups_selected and not any(r[g][-1] for r in train for g in groups_selected):
     continue
    def vec(x):return x['base']+[v for group in groups_selected for v in x[group]]
    model=make_pipeline(StandardScaler(),Ridge(alpha=100))
    model.fit(np.asarray([vec(r) for r in train]),np.asarray([r['actual'] for r in train]))
    pred=model.predict(np.asarray([vec(r) for r in test]))
    for r,p in zip(test,pred):
     pred=max(0,float(p))
     pred=min(r['baseline']*1.25,max(r['baseline']*.75,pred))
     outcomes[name].append((key,abs(pred-r['actual']),abs(r['baseline']-r['actual'])))
  scored_rows=outcomes['combined'] if outcomes['combined'] else outcomes['baseline_features']
  market_report={'holdout_weeks':len(set(k for k,_,_ in scored_rows)),
    'holdout_rows':len(scored_rows),
    'source_coverage':{k:sum(r[k][-1]>0 for r in items) for k in ('ngs','snap','pfr')},
    'models':{}}
  for name,scored in outcomes.items():
   if len(scored)<min_test:
    market_report['models'][name]={'status':'insufficient_holdout','samples':len(scored)}
    continue
   baseline=sum(z[2] for z in scored)/len(scored)
   mae=sum(z[1] for z in scored)/len(scored)
   market_report['models'][name]={'status':'evaluated','samples':len(scored),
      'baseline_mae':round(baseline,3),'challenger_mae':round(mae,3),
      'improvement_pct':round((baseline-mae)/baseline*100,2) if baseline else None,
      'eligible_for_production':False}
  report[market]=market_report
 return report

def main():
 import nflreadpy as nfl
 p=argparse.ArgumentParser()
 p.add_argument('--input',type=Path,default=Path('data/weekly-player-ml-training.csv'))
 p.add_argument('--start',type=int,default=2018)
 p.add_argument('--end',type=int,default=datetime.now(timezone.utc).year)
 p.add_argument('--output',type=Path,default=Path('data/research-free-nfl-features.json'))
 a=p.parse_args()
 if a.start<2016 or a.end<a.start or a.end>datetime.now(timezone.utc).year:raise SystemExit('Invalid season interval')
 with a.input.open(newline='',encoding='utf-8-sig') as f:raw=list(csv.DictReader(f))
 datasets=load_sources(nfl,list(range(a.start,a.end+1)))
 series,pfr,coverage=assemble_index(datasets)
 rows=enriched_rows(raw,series,pfr)
 report={'generated_at_utc':datetime.now(timezone.utc).isoformat(),
  'research_only':True,'production_changed':False,'automatic_promotion':False,
  'training_data_start':a.start,'training_data_end':a.end,
  'source_coverage':coverage,'markets':assess(rows),
  'limitations':[
   'Only NGS, PFR snap counts and advanced weekly PFR stats are fitted in this first ablation.',
   'Injury and depth-chart records are inventoried but excluded without verified pregame as-of timestamps.',
   'NOAA historical observations and NWS forecast snapshots are not fitted without a timestamp-safe weather history join.',
   'NGS reports only players meeting activity thresholds; missing is not zero performance.',
   'PFR joins use official GSIS/PFR mapping only; player names are never used to force identity.',
   'Retrospective prior-week features are not frozen live forecasts and cannot directly promote production.'
  ]}
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(report,indent=2)+'\n')
 # Export model coefficients and strictly prior-week player source vectors for
 # matching live ML card *research estimates* (never change production picks).
 from research.select_market_ml import select
 from research.publish_advanced_player_ml import write_outputs
 target=json.loads(Path('data/live-v2.json').read_text())
 season,week=int(target['season']),int(target['week'])
 game_runtime=json.loads(Path('data/game-ml-runtime.json').read_text())
 selection=select(report,game_runtime)
 Path('data/market-ml-research-selection.json').write_text(json.dumps(selection,indent=2)+'\n')
 player_feed=json.loads(Path('data/player-research.json').read_text())
 pids=[r.get('player_id') for r in player_feed.get('players',[])
       if r.get('stat_key') in MARKET_SOURCE
       and r.get('game_id') in {g.get('game_id') for g in target.get('games',[])}]
 runtime,snapshot=write_outputs(rows,series,pfr,selection,season,week,pids,
    Path('data/player-advanced-ml-runtime.json'),Path('data/player-advanced-ml-features.json'))
 print('Advanced ML shadow models:',list(runtime['models']),
       'current player feature vectors:',len(snapshot['players']))
 print(json.dumps({'markets':report['markets'],'source_coverage':coverage},indent=2))
if __name__=='__main__':main()
