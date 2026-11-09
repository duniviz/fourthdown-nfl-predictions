import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from scripts.publish_model_lab import publish

class PublishLabTests(unittest.TestCase):
    def test_optional_reports_are_valid_json_and_other_data_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            artifact=root/'research.zip'
            unrelated=root/'untouched.json'
            unrelated.write_text('{"value":7}\n')
            with zipfile.ZipFile(artifact,'w') as archive:
                archive.writestr('research/v3-results/results.json','{"markets":{}}')
                archive.writestr('research/auto-promotion/readiness.json','{"status":"waiting"}')
                archive.writestr('research/paired-game-results/report.json','{"pick_results":[]}')
            written=publish(artifact,root,datetime(2026,11,8,tzinfo=timezone.utc))
            self.assertEqual(len(written),3)
            for path in written:
                json.loads(path.read_text())
                self.assertTrue(path.read_text().endswith('\n'))
            self.assertEqual(json.loads(unrelated.read_text()),{'value':7})
            self.assertFalse((root/'model-lab-yardage-game.json').exists())
            paired=json.loads((root/'model-lab-paired-games.json').read_text())
            self.assertEqual(paired['pick_results'],[])
            self.assertEqual(paired['published_at_utc'],'2026-11-08T00:00:00+00:00')

if __name__=='__main__':unittest.main()
