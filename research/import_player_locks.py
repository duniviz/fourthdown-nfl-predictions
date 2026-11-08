"""Import archived pregame production projections for paired model evaluation."""
import json
from pathlib import Path
from live.game_pregame_observations import dt
from research.join_frozen_pregame_results import norm

def merge(snapshots, existing):
    indexed={(str(r['game_id']),str(r['player_id']),str(r['stat_key']),str(r['model'])):r for r in existing}
    for row in snapshots:
        kickoff=dt(row.get('kickoff'))
        predicted=dt(row.get('captured_at'))
        saved=dt(row.get('saved_at_utc'))
        quote=dt(row.get('dk_captured_at'))
        if not kickoff or not predicted or not saved or not predicted<=saved<kickoff:
            continue
        key=(str(row.get('game_id')),str(row.get('player_id')),norm(row.get('market')),'live')
        if not all(key) or 'None' in key:
            continue
        line=row.get('dk_line') if quote and quote<=saved else None
        for existing_key in list(indexed):
            if existing_key[0]==key[0] and existing_key[1]==key[1] and norm(existing_key[2])==key[2] and existing_key[3]=='live':
                del indexed[existing_key]
        indexed[key]={'game_id':key[0], 'player_id':key[1], 'stat_key':key[2], 'model':'live',
                      'projection':row.get('projection'), 'dk_line':line, 'kickoff_utc':kickoff.isoformat(),
                      'predicted_at_utc':predicted.isoformat(), 'source':'archived production player projection', 'actual':None}
    return sorted(indexed.values(),key=lambda r:(str(r['game_id']),str(r['player_id']),str(r['stat_key']),str(r['model'])))

def main():
    data=Path('data')
    path=data/'weekly-shadow-forecasts.json'
    old=json.loads(path.read_text()) if path.exists() else {'rows':[]}
    snapshots=json.loads((data/'pregame-snapshots.json').read_text()).get('records',[])
    old['rows']=merge(snapshots,old['rows'])
    path.write_text(json.dumps(old,indent=2)+'\n')
    print('Imported production player forecasts:',len(old['rows']))
if __name__=='__main__':main()
