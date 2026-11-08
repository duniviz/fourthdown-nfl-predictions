import json
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from scripts.publish_weekly_lab import publish,REPORTS

class WeeklyLabTests(unittest.TestCase):
    def test_publish_and_reject_incomplete_reports(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'data').mkdir()
            for source,_ in REPORTS:
                path=root/source
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(json.dumps({'matched_slate_records':0,'metrics':[],'status':'WAITING_FOR_FINALS'}))
            self.assertEqual(publish(root,datetime(2026,11,8,tzinfo=timezone.utc)),2)
            for _,target in REPORTS:
                report=json.loads((root/target).read_text())
                self.assertEqual(report['status'],'WAITING_FOR_FINALS')
                self.assertEqual(report['matched_slate_records'],0)
            (root/REPORTS[1][0]).write_text('{"metrics":[]}')
            with self.assertRaises(ValueError):publish(root,datetime.now(timezone.utc))

if __name__=='__main__':unittest.main()
