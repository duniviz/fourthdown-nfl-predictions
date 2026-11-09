"""Publish validated Model Lab reports from a downloaded research artifact."""
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SOURCES = (
    ('research/v3-results/results.json', 'model-lab-results.json'),
    ('research/auto-promotion/readiness.json', 'model-lab-readiness.json'),
    ('research/paired-game-results/report.json', 'model-lab-paired-games.json'),
)

def publish(artifact, destination, now):
    written = []
    with zipfile.ZipFile(artifact) as archive:
        for source, filename in SOURCES:
            names = [name for name in archive.namelist()
                     if name.endswith(source) or name.endswith(source.removeprefix('research/'))]
            if not names:
                print(f'Missing {source}; keeping existing published file')
                continue
            if len(names) != 1:
                raise ValueError(f'Ambiguous research artifact: {source}')
            report = json.loads(archive.read(names[0]))
            if not isinstance(report, dict):
                raise ValueError(f'Invalid research report: {source}')
            if filename == 'model-lab-results.json':
                if not isinstance(report.get('markets'), dict):
                    raise ValueError('Research markets missing')
                report['generated_at_utc'] = now.isoformat()
            elif filename == 'model-lab-paired-games.json':
                if not isinstance(report.get('pick_results'), list):
                    raise ValueError('Paired game pick results missing')
                report['published_at_utc'] = now.isoformat()
            target = destination / filename
            target.write_text(json.dumps(report, indent=2) + '\n')
            written.append(target)
    return written

if __name__ == '__main__':
    publish(Path(sys.argv[1]), Path('data'), datetime.now(timezone.utc))
