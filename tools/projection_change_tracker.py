"""Compact, strictly pre-lock projection history for the site (never changes forecasts)."""
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ALIASES = {'player_pass_yds':'passing_yards','player_passing_yards':'passing_yards','passing_yards':'passing_yards',
           'player_rush_yds':'rushing_yards','player_rushing_yards':'rushing_yards','rushing_yards':'rushing_yards',
           'player_rec_yds':'receiving_yards','player_reception_yds':'receiving_yards','player_receiving_yards':'receiving_yards','receiving_yards':'receiving_yards',
           'player_pass_completions':'completions','completions':'completions',
           'player_rush_attempts':'carries','rush_attempts':'carries','carries':'carries',
           'player_receptions':'receptions','receptions':'receptions'}

def dt(value):
    try:
        d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (ValueError,TypeError): return None

def num(value):
    if value is None or isinstance(value,bool): return None
    try:
        n=float(value)
        return n if math.isfinite(n) else None
    except (ValueError,TypeError): return None

def build(schedule, game_rows, player_rows, now):
    """Use only observations demonstrably saved at or before each game's T-15 cutoff."""
    games={str(g.get('game_id')):g for g in schedule if g.get('game_id') and dt(g.get('kickoff_utc'))}
    out={'schema_version':1,'games':{},'players':{}}
    game_versions=defaultdict(dict); player_versions=defaultdict(dict)
    def valid(row, timestamp, saved, game):
        start=dt(game.get('kickoff_utc')); t=dt(timestamp); saved_at=dt(saved)
        return bool(start and t and saved_at and t<=saved_at<=min(now,start-timedelta(minutes=15)) and t<=now)
    for r in game_rows:
        gid=str(r.get('game_id')); g=games.get(gid)
        if not g or not valid(r,r.get('forecast_at_utc'),r.get('captured_at_utc'),g): continue
        h,a=num(r.get('projected_home_score')),num(r.get('projected_away_score'))
        if h is None or a is None: continue
        stamp=dt(r['forecast_at_utc']).isoformat()
        game_versions[gid][stamp]={'at':stamp,'home':h,'away':a}
    for r in player_rows:
        gid=str(r.get('game_id')); g=games.get(gid)
        if not g or not r.get('player_id') or not valid(r,r.get('forecast_captured_at_utc'),r.get('saved_at_utc'),g):continue
        market=ALIASES.get(str(r.get('stat_key') or r.get('market_key') or '').lower())
        value=num(r.get('projection'))
        if not market or value is None:continue
        stamp=dt(r['forecast_captured_at_utc']).isoformat()
        key='|'.join((gid,str(r['player_id']),market))
        player_versions[key][stamp]={'at':stamp,'value':value}
    for key, versions in game_versions.items():out['games'][key]=[versions[t] for t in sorted(versions,key=dt)]
    for key, versions in player_versions.items():out['players'][key]=[versions[t] for t in sorted(versions,key=dt)]
    return out

def main(data=Path('data'),now=None):
    def read(name,default):
        p=data/name
        return json.loads(p.read_text()) if p.exists() else default
    result=build(read('live-v2.json',{}).get('games',[]),read('game-pregame-observations.json',{}).get('records',[]),read('player-history.json',{}).get('players',[]),now or datetime.now(timezone.utc))
    previous=read('projection-changes.json',{})
    current_ids={str(g.get('game_id')) for g in read('live-v2.json',{}).get('games',[])}
    for kind in ('games','players'):
        for key, versions in previous.get(kind,{}).items():
            if key.split('|',1)[0] not in current_ids and key not in result[kind]:
                result[kind][key]=versions
    (data/'projection-changes.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print('Projection histories:',len(result['games']),'games,',len(result['players']),'player markets')

if __name__=='__main__':main()
