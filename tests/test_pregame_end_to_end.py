import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from live.dk_identity import QuoteIndex, norm, market as canonical_market, team as team_code
from scripts.capture_pregame_snapshots import capture
from research.join_frozen_pregame_results import join

class PregameIntegration(unittest.TestCase):
 def test_actual_pitts_quote_through_capture_and_grading(self):
  data=Path('data')
  odds=json.loads((data/'dk-pregame-lines.json').read_text())['rows']
  quote_row=next(q for q in odds if norm(q.get('player'))==norm('Kyle Pitts')
                 and canonical_market(q.get('market_key') or q.get('market')) in ('player_rec_yds','receiving_yards')
                 and float(q.get('line',0))==43.5)
  kickoff=datetime.fromisoformat(quote_row['commence_time'].replace('Z','+00:00'))
  now=datetime.fromisoformat('2026-11-08T14:10:00+00:00')
  home,away=team_code(quote_row['home_team']),team_code(quote_row['away_team'])
  self.assertIn('ATL',(home,away))
  player_team='ATL'
  player={'game_id':quote_row.get('game_id') or 'regression-atl-cin',
          'player_id':quote_row.get('player_id') or 'regression-kyle-pitts',
          'player':'Kyle Pitts','team':player_team,'opponent':away if home==player_team else home,
          'market_key':'player_receiving_yards','stat_key':'receiving_yards','projection':56.0,
          'generated_at_utc':'2026-11-08T14:00:00+00:00'}
  quote=QuoteIndex(odds,now).find(player,kickoff)
  self.assertIsNotNone(quote)
  self.assertEqual(quote[3],43.5)
  rows=capture([], [player], odds,{player['game_id']:kickoff},now)
  self.assertEqual(rows[0]['dk_line'],43.5)
  result=join(rows,[{'game_id':player['game_id'],'player_id':player['player_id'],'stat_key':'receiving_yards','actual':50}])
  self.assertEqual(result['rows'][0]['dk_line'],43.5)
  self.assertEqual(capture(rows,[player],odds,{player['game_id']:kickoff},kickoff+timedelta(minutes=1)),rows)
 def test_suffixes_and_matchup(self):
  for suffix in ('Sr.','Jr.','II','III','IV','V','Senior','Junior'):
   self.assertEqual(norm('Kyle Pitts '+suffix),norm('Kyle Pitts'))
  self.assertNotEqual(norm('Kyle Pitts'),norm('Kyle Trask'))
