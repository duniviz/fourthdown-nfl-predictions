import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from scripts import freeze_count_ml_predictions as freeze

class XGBoostCountFreezeTests(unittest.TestCase):
    def test_same_market_shares_training_and_preserves_pregame_cutoff(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            def put(name, data): (root/name).write_text(json.dumps(data))
            rows=[]; results=[]
            for i in range(32):
                game=f'2026_{1+i%2:02d}_A_B'; player=f'p{i}'
                rows.append({'game_id':game,'player_id':player,'stat_key':'player_receptions','model':'live','projection':4,
                             'kickoff_utc':'2026-10-10T18:00:00+00:00','predicted_at_utc':'2026-10-10T17:00:00+00:00'})
                results.append({'game_id':game,'player_id':player,'stat_key':'receptions','actual':i%8})
            put('weekly-shadow-forecasts.json',{'rows':rows})
            put('player-results.json',{'rows':results})
            put('pregame-snapshots.json',{'records':[]})
            put('live-v2.json',{'games':[{'game_id':'2026_03_A_B','season':2026,'week':3,'kickoff_utc':'2026-12-01T18:00:00+00:00'}]})
            put('count-projections.json',{'generated_at_utc':'2026-11-01T10:00:00+00:00','players':[
                {'game_id':'2026_03_A_B','player_id':p,'market_key':'player_receptions','projection':4} for p in ('one','two')]})
            with patch.object(freeze,'DATA',root):
                out=freeze.build(datetime(2026,11,1,11,tzinfo=timezone.utc))
            added=[r for r in out if r.get('model')=='ml_count_xgboost']
            self.assertEqual({r['player_id'] for r in added},{'one','two'})
            self.assertTrue(all(r['predicted_at_utc'] < r['kickoff_utc'] for r in added))

if __name__=='__main__': unittest.main()
