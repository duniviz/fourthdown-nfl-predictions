"""Publish the weekly frozen-forecast leaderboards consumed by Model Lab."""
import json
from datetime import datetime, timezone
from pathlib import Path

REPORTS = (
    ('research/yardage-game-results/leaderboard.json', 'data/model-lab-yardage-game.json'),
    ('research/weekly-shadow-results/leaderboard.json', 'data/model-lab-weekly-shadow.json'),
)

def publish(root, now):
    reports=[]
    for source, target in REPORTS:
        report=json.loads((root/source).read_text())
        if not isinstance(report,dict) or not isinstance(report.get('metrics'),list):
            raise ValueError(f'Invalid weekly leaderboard: {source}')
        if not isinstance(report.get('matched_slate_records'),int):
            raise ValueError(f'Missing matched-slate count: {source}')
        report['published_at_utc']=now.isoformat()
        reports.append((root/target,report))
    for target,report in reports:
        target.write_text(json.dumps(report,indent=2)+'\n')
    return len(reports)

if __name__=='__main__':
    print(f'Published {publish(Path.cwd(),datetime.now(timezone.utc))} weekly leaderboards')
