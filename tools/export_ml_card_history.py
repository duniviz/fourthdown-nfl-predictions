"""Publish a compact, validated training source for research ML card models.

Inputs are the completed-game, prior-week retrospective rebuild; never present
these rows as frozen live forecasts. The consumer also enforces target cutoff.
"""
import argparse,csv,gzip,hashlib,io,json,math,os,tempfile
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

FIELDS=('season','week','player_id','market','new','old','actual','prior_games','recent_volume','recent_yards')
MARKETS={'passing_yards','rushing_yards','receiving_yards'}

def export(source,output,metadata,min_season=2016,min_rows=100):
    counts=Counter();seasons=Counter();seen=set();duplicates=set();rows=[]
    with source.open(newline='',encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            try:
                season=int(r['season']);week=int(r['week']);market=r['market'];pid=str(r['player_id']).strip()
                vals=[float(r[k]) for k in ('new','old','actual','prior_games','recent_volume','recent_yards')]
                if season<min_season or not 1<=week<=22 or not pid or market not in MARKETS or any(not math.isfinite(x) or x<0 for x in vals):continue
                key=(season,week,pid,market)
                if key in seen:duplicates.add(key)
                seen.add(key)
                rows.append((key,[season,week,pid,market,*vals]))
            except (KeyError,TypeError,ValueError):continue
    # Ambiguous identities are removed in full, including the first occurrence.
    clean=[]
    for key,row in rows:
        if key in duplicates:continue
        clean.append(row);counts[row[3]]+=1;seasons[str(row[0])]+=1
    if min_season not in {int(y) for y in seasons} or any(counts[m]<min_rows for m in MARKETS):
        raise ValueError('Insufficient validated player-history coverage; preserving previous archive')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent,delete=False) as t:
        tmp=Path(t.name)
        with gzip.GzipFile(fileobj=t,mode='wb',mtime=0) as gz:
            with io.TextIOWrapper(gz,encoding='utf-8',newline='') as text:
                writer=csv.writer(text);writer.writerow(FIELDS);writer.writerows(clean)
    digest=hashlib.sha256(tmp.read_bytes()).hexdigest()
    report={'schema_version':2,'source':'completed-game prior-week retrospective player backtests',
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),'sha256':digest,
        'rows':len(clean),'season_rows':dict(sorted(seasons.items())),
        'market_rows':dict(counts),'ambiguous_identities_excluded':len(duplicates),
        'note':'Retrospective training data, not saved live pregame forecasts; target week must be excluded.'}
    meta_temp=metadata.with_suffix('.tmp');meta_temp.write_text(json.dumps(report,indent=2)+'\n')
    os.replace(tmp,output);os.replace(meta_temp,metadata)
    print(f"Validated {len(clean)} rows across seasons {', '.join(sorted(seasons))}; excluded {len(duplicates)} ambiguous identities")
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=Path('data/weekly-player-ml-training.csv'))
    p.add_argument('--output',type=Path,default=Path('data/ml-card-training.csv.gz'))
    p.add_argument('--metadata',type=Path,default=Path('data/ml-card-training-meta.json'))
    a=p.parse_args();export(a.input,a.output,a.metadata)
if __name__=='__main__':main()
