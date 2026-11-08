import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from live.dk_identity import QuoteIndex, norm
from scripts.capture_pregame_snapshots import capture
from research.join_frozen_pregame_results import join

class PregameIntegration(unittest.TestCase):
 def test_actual_pitts_quote_through_capture_and_grading(self):
  data=Path('data')
  odds=json.loads((data/'dk-pregame-lines.json').read_text())['rows']
  research=json.loads((data/'player-research.json').read_text())
  player=next(p for p in research['players'] if p['player']=='Kyle Pitts' and p['stat_key']=='receiving_yards')
  kickoff=datetime.fromisoformat('2026-11-08T14:30:00+00:00')
  now=datetime.fromisoformat('2026-11-08T14:10:00+00:00')
  player={**player,'generated_at_utc':research['generated_at_utc']}
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
