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
from research.player_opportunity_features import add_weekly_features
from research.ftn_player_features import load_joined,add_charted_features
from research.pbp_situational_features import load_completed_pbp,add_situational_features
from live.player_ml_feature_groups import GROUPS

MARKET_SOURCE={'passing_yards':'passing','rushing_yards':'rushing','receiving_yards':'receiving'}
NGS_METRICS={
 'passing':('avg_time_to_throw','avg_completed_air_yards','completion_percentage_above_expectation'),
 'receiving':('avg_separation','avg_cushion','avg_intended_air_yards'),
 'rushing':('efficiency','avg_time_to_los','rush_yards_over_expected_per_att'),
}
# PFR player IDs are not GSIS IDs. Never join by player names alone.
PFR_METRICS={
 'pass':('times_pressured_pct','passing_bad_throw_pct','passing_drop_pct'),
 'rush':('rushing_yards_before_contact_avg','rushing_yards_after_contact_avg','rushing_broken_tackles'),
 'rec':('receiving_drop_pct','receiving_rat','receiving_broken_tackles'),
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
  finals=set()
  try:
   games=nfl.load_schedules([season]).to_dicts()
   finals={str(g['game_id']) for g in games if g.get('game_type')=='REG' and g.get('game_id') and g.get('home_score') is not None and g.get('away_score') is not None}
   frame=nfl.load_player_stats([season],summary_level='week')
   columns=('season','week','season_type','game_id','player_id','team','opponent_team',
            'target_share','air_yards_share','receiving_air_yards','receiving_yards','receiving_epa','receiving_20','targets',
            'carries','rushing_yards','rushing_epa','rushing_10',
            'attempts','passing_yards','passing_epa','passing_20')
   stats=frame.select([c for c in columns if c in frame.columns]).to_dicts()
   datasets[f'weekly_{season}']=[r for r in stats if str(r.get('game_id') or '') in finals]
  except Exception as exc:
   print('SOURCE_UNAVAILABLE',f'weekly_{season}',type(exc).__name__,str(exc)[:170])
  if finals:
   try:datasets[f'situational_{season}']=load_completed_pbp(nfl,season,finals)
   except Exception as exc:
    print('SOURCE_UNAVAILABLE',f'situational_{season}',type(exc).__name__,str(exc)[:170])
   try:datasets[f'ftn_{season}']=load_joined(nfl,season,finals)
   except Exception as exc:
    print('SOURCE_UNAVAILABLE',f'ftn_{season}',type(exc).__name__,str(exc)[:170])
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
   try:datasets[name]=[r for r in nfl.load_pfr_advstats([season],stat_type=kind,summary_level='week').to_dicts() if str(r.get('game_id') or '') in finals]
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
    if kind=='rush':
     carries=valid(r.get('carries'))
     vals[2]=vals[2]/carries if vals[2] is not None and carries and carries>0 else None
    if pid and any(x is not None for x in vals):
     series[(f'pfr_{kind}',str(pid))].append((k,vals))
     coverage[source]['eligible_rows']+=1
  if source.startswith('weekly_'):
   completed={str(r.get('game_id')) for r in rows if r.get('game_id')}
   coverage[source]['eligible_rows']=add_weekly_features(series,rows,completed)
  if source.startswith('ftn_'):
   coverage[source]['eligible_rows']=add_charted_features(series,rows)
  if source.startswith('situational_'):
   coverage[source]['eligible_rows']=add_situational_features(series,rows)
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

def complete_lagged_values(series,source,pid,target,n):
 """Require every new feature to be observed; missing is never a real zero."""
 eligible=[v for k,v in series.get((source,str(pid)),[]) if k<target and
           k[0]>=target[0]-1 and (k[0]!=target[0] or k[1]>=target[1]-8)][-4:]
 if not eligible or any(not any(i<len(v) and v[i] is not None for v in eligible) for i in range(n)):
  return [0.0]*n,0.0
 return [sum(v[i] for v in eligible if i<len(v) and v[i] is not None)/
         sum(i<len(v) and v[i] is not None for v in eligible) for i in range(n)],1.0

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
  pfr_data,pfr_seen=complete_lagged_values(series,'pfr_'+MARKET_PFR[market],pfr,target,3) if pfr else ([0.0]*3,0.0)
  workload,workload_seen=lagged_values(series,'workload_'+market,pid,target,3)
  opponent,opponent_seen=lagged_values(series,'matchup_'+market,r.get('opponent'),target,3)
  ftn,ftn_seen=complete_lagged_values(series,'ftn_'+market,pid,target,3)
  ftn_def,ftn_def_seen=complete_lagged_values(series,'ftn_defense_'+market,r.get('opponent'),target,3)
  situational,situational_seen=complete_lagged_values(series,'situational_'+market,pid,target,3)
  base=[*values[:7],float(target[1])]
  out.append({'market':market,'key':target,'player_id':str(pid),'baseline':values[0],'actual':values[-1],
              'team':str(r.get('team') or ''),'opponent':str(r.get('opponent') or ''),
              'base':base,'ngs':ngs+[ngs_seen],'snap':snap+[snap_seen],
              'pfr':[0.0]*4, 'pfr_new':pfr_data+[pfr_seen], 'workload':workload+[workload_seen],
              'matchup':opponent+[opponent_seen], 'ftn':ftn+[ftn_seen],
              'ftn_defense':ftn_def+[ftn_def_seen], 'situational':situational+[situational_seen]})
 return out

def assess(rows,min_train=100,min_test=30,incumbents=None):
 report={}
 for market in MARKET_SOURCE:
  items=sorted([r for r in rows if r['market']==market],key=lambda r:(r['key'],r['player_id']))
  groups=sorted({r['key'] for r in items})
  # Reserve the final four weeks as an independent confirmation set for
  # choosing new feature groups. Model fitting itself is strictly earlier-week.
  holdouts=groups[-12:]
  selection_keys=set(holdouts[:-4])
  confirmation_keys=set(holdouts[-4:])
  outcomes=defaultdict(list)
  for key in holdouts:
   train=[r for r in items if r['key']<key]
   test=[r for r in items if r['key']==key]
   if len(train)<min_train or not test:continue
   for name,groups_selected in GROUPS.items():
    # Do not call a dataset a feature improvement when it was unavailable.
    if any(not any(r.get(g,[0])[-1] for r in train) for g in groups_selected if g in ('workload','matchup','pfr_new','ftn','ftn_defense','situational')):
     continue
    if groups_selected and not any(r.get(g,[0])[-1] for r in train for g in groups_selected):
     continue
    def vec(x):return x['base']+[v for group in groups_selected for v in x.get(group,[0.0]*4)]
    model=make_pipeline(StandardScaler(),Ridge(alpha=100))
    model.fit(np.asarray([vec(r) for r in train]),np.asarray([r['actual'] for r in train]))
    pred=model.predict(np.asarray([vec(r) for r in test]))
    for r,p in zip(test,pred):
     pred=max(0,float(p))
     pred=min(r['baseline']*1.25,max(r['baseline']*.75,pred))
     outcomes[name].append((key,abs(pred-r['actual']),abs(r['baseline']-r['actual']),r))
  scored_rows=outcomes['combined'] if outcomes['combined'] else outcomes['baseline_features']
  market_report={'holdout_weeks':len(set(z[0] for z in scored_rows)),
    'holdout_rows':len(scored_rows),
    'source_coverage':{k:sum(r.get(k,[0])[-1]>0 for r in items) for k in ('ngs','snap','pfr','pfr_new','ftn','ftn_defense','workload','matchup','situational')},
    'models':{}}
  for name,scored in outcomes.items():
   if len(scored)<min_test:
    market_report['models'][name]={'status':'insufficient_holdout','samples':len(scored)}
    continue
   baseline=sum(z[2] for z in scored)/len(scored)
   mae=sum(z[1] for z in scored)/len(scored)
   selection=[z for z in scored if z[0] in selection_keys]
   confirmation=[z for z in scored if z[0] in confirmation_keys]
   market_report['models'][name]={'status':'evaluated','samples':len(scored),
      'baseline_mae':round(baseline,3),'challenger_mae':round(mae,3),
      'improvement_pct':round((baseline-mae)/baseline*100,2) if baseline else None,
      'selection_samples':len(selection),
      'selection_weeks':len({z[0] for z in selection}),
      'selection_mae':round(sum(z[1] for z in selection)/len(selection),4) if selection else None,
      'confirmation_samples':len(confirmation),
      'confirmation_weeks':len({z[0] for z in confirmation}),
      'confirmation_mae':round(sum(z[1] for z in confirmation)/len(confirmation),4) if confirmation else None,
      'eligible_for_production':False}
  # Compare the new variants with each established feature variant on the
  # exact same player/week rows where the new inputs exist. Select using the
  # earlier holdout weeks; the final weeks are reserved for confirmation.
  legacy=('baseline_features','ngs','snap_counts','combined','pfr_advanced')
  novel={'weekly_workload':('workload',),'opponent_efficiency':('matchup',),
         'workload_matchup':('workload','matchup'),
         'advanced_workload':('workload',),'advanced_matchup':('matchup',),
         'advanced_all':('workload','matchup')}
  market_report['new_feature_comparisons']={}
  for name,required in novel.items():
   def identity(z):
    return (z[0],z[3]['player_id'],z[3].get('team'),z[3].get('opponent'))
   rows_by_key={identity(z):z for z in outcomes.get(name,[])
                if all(z[3].get(group,[0])[-1]>0 for group in required)
                and (not name.startswith('advanced_') or any(z[3].get(g,[0])[-1]>0 for g in ('ngs','snap','pfr')))}
   comparisons=[]
   for ref in legacy:
    groups_for_ref={'ngs':('ngs',),'snap_counts':('snap',),'pfr_advanced':('pfr',),
                    'combined':('ngs','snap','pfr')}.get(ref,())
    reference={identity(z):z for z in outcomes.get(ref,[])
               if not groups_for_ref or any(z[3].get(g,[0])[-1]>0 for g in groups_for_ref)}
    same=set(rows_by_key)&set(reference)
    def pair_metrics(keys):
     if not keys:return None
     return {'samples':len(keys),'weeks':len({k[0] for k in keys}),
       'candidate_mae':sum(rows_by_key[k][1] for k in keys)/len(keys),
       'reference_mae':sum(reference[k][1] for k in keys)/len(keys),
       'candidate_rmse':math.sqrt(sum(rows_by_key[k][1]**2 for k in keys)/len(keys)),
       'reference_rmse':math.sqrt(sum(reference[k][1]**2 for k in keys)/len(keys))}
    sel=pair_metrics([k for k in same if k[0] in selection_keys])
    conf=pair_metrics([k for k in same if k[0] in confirmation_keys])
    if sel and conf:comparisons.append((sel['reference_mae'],ref,sel,conf))
   if comparisons:
    _,ref,sel,conf=min(comparisons,key=lambda x:x[0])
    market_report['new_feature_comparisons'][name]={'reference':ref,'selection':sel,'confirmation':conf}
  # New PFR/FTN candidates must beat the actually published ML-card variant,
  # not just a simpler baseline, on matched eligible historical player games.
  from research.select_market_ml import choose_player
  legacy_winner=choose_player(market,market_report).get('research_winner')
  incumbent=(incumbents or {}).get(market) or legacy_winner
  market_report['pfr_ftn_comparisons']={}
  market_report['pfr_ftn_incumbent']=incumbent
  fresh_names=('pfr_fixed','ftn_player','ftn_opponent','pfr_ftn','pfr_plus',
               'ftn_plus','ftn_opponent_plus','pfr_ftn_plus','all_new','situational','situational_plus')
  def ident(z):return (z[0],z[3]['player_id'],z[3].get('team'),z[3].get('opponent'))
  def eligible(z,variant):
   feature=z[3]; groups=GROUPS.get(variant,())
   if any(feature.get(g,[0])[-1]<=0 for g in groups if g in ('workload','matchup','pfr_new','ftn','ftn_defense','situational')):return False
   if variant.startswith('advanced_') and not any(feature.get(g,[0])[-1]>0 for g in ('ngs','snap','pfr')):return False
   return not groups or any(feature.get(g,[0])[-1]>0 for g in groups)
  reference={ident(z):z for z in outcomes.get(incumbent,[]) if eligible(z,incumbent)}
  for name in fresh_names:
   candidate={ident(z):z for z in outcomes.get(name,[]) if eligible(z,name)}
   same=set(candidate)&set(reference)
   def paired(keys):
    if not keys:return None
    return {'samples':len(keys),'weeks':len({k[0] for k in keys}),
      'candidate_mae':sum(candidate[k][1] for k in keys)/len(keys),
      'reference_mae':sum(reference[k][1] for k in keys)/len(keys),
      'candidate_rmse':math.sqrt(sum(candidate[k][1]**2 for k in keys)/len(keys)),
      'reference_rmse':math.sqrt(sum(reference[k][1]**2 for k in keys)/len(keys))}
   sel=paired([k for k in same if k[0] in selection_keys])
   conf=paired([k for k in same if k[0] in confirmation_keys])
   if sel and conf:market_report['pfr_ftn_comparisons'][name]={'reference':incumbent,'selection':sel,'confirmation':conf}
  # On future weeks, compare an already-selected new-source candidate with the
  # strongest established variant, so it can be retained or rolled back.
  if incumbent in fresh_names and legacy_winner:
   candidate={ident(z):z for z in outcomes.get(incumbent,[]) if eligible(z,incumbent)}
   reference={ident(z):z for z in outcomes.get(legacy_winner,[]) if eligible(z,legacy_winner)}
   same=set(candidate)&set(reference)
   sel=paired([k for k in same if k[0] in selection_keys])
   conf=paired([k for k in same if k[0] in confirmation_keys])
   if sel and conf:market_report['pfr_ftn_retention']={'reference':legacy_winner,'selection':sel,'confirmation':conf}
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
 current_runtime=json.loads(Path('data/player-advanced-ml-runtime.json').read_text())
 incumbents={market:model.get('variant') for market,model in current_runtime.get('models',{}).items()}
 report={'generated_at_utc':datetime.now(timezone.utc).isoformat(),
  'research_only':True,'production_changed':False,'automatic_promotion':False,
  'training_data_start':a.start,'training_data_end':a.end,
  'source_coverage':coverage,'markets':assess(rows,incumbents=incumbents),
  'limitations':[
   'Weekly opportunity and opponent efficiency are derived only from verified completed games and lagged before each forecast.',
   'Situational play-by-play rates use uniquely identified completed-game plays and strictly prior weeks.',
   'Injury and depth-chart records are inventoried but excluded without verified pregame as-of timestamps.',
   'NOAA historical observations and NWS forecast snapshots are not fitted without a timestamp-safe weather history join.',
   'NGS reports only players meeting activity thresholds; missing is not zero performance.',
   'PFR joins use official GSIS/PFR mapping only; player names are never used to force identity.',
   'FTN Data via nflverse, CC BY-SA 4.0; joined on unique game and play IDs.',
   'PFR and FTN historical archives can contain later corrections; historical rows are not verified pregame as-of snapshots.',
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
 pids=[r for r in player_feed.get('players',[])
       if r.get('stat_key') in MARKET_SOURCE
       and r.get('game_id') in {g.get('game_id') for g in target.get('games',[])}]
 runtime,snapshot=write_outputs(rows,series,pfr,selection,season,week,pids,
    Path('data/player-advanced-ml-runtime.json'),Path('data/player-advanced-ml-features.json'))
 print('Advanced ML shadow models:',list(runtime['models']),
       'current player feature vectors:',len(snapshot['players']))
 print(json.dumps({'markets':report['markets'],'source_coverage':coverage},indent=2))
if __name__=='__main__':main()
