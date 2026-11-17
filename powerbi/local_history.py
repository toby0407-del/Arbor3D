"""All stored park quarters in a separate local Desktop model, preserving provenance."""
import argparse
import json
from pathlib import Path
from analytics.core import FIELDS
from analytics.park_scenarios import generate as export_quarters
from powerbi.build_project import generate
from powerbi.local_app import verify_overview


def prepare(output):
    output=Path(output)
    counts=export_quarters(output)
    generate(output/'analytics',output/'powerbi',clean_titles=True)
    result=dict(counts=counts,desktop_validated=False,
                project=str((output/'powerbi/Arbor3D.pbip').resolve()),
                notes=['All 16 quarters, separate from current App snapshots to avoid double-counting.',
                       'Source kind retained in the data-source page and underlying tables.'])
    (output/'history-delivery.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def verify(folder,results):
    folder=Path(folder)
    tables=json.loads((folder/'analytics/analytics.json').read_text(encoding='utf-8'))['tables']
    evidence=json.loads(Path(results).read_text(encoding='utf-8-sig'))
    if evidence.get('engine')!='Power BI Desktop / Analysis Services': raise ValueError('Desktop evidence required')
    for name in ('DimScan','FactObservation','FactEstimate','FactGrowth'):
        def normalized(rows):
            clean=[{k:None if v == "" else round(v,8) if isinstance(v,float) else v for k,v in row.items()} for row in rows]
            return sorted(json.dumps(row,sort_keys=True,ensure_ascii=False) for row in clean)
        # Tabular integers and doubles compare numerically, not by their JSON spelling.
        def numeric(rows):
            return [{k:float(v) if isinstance(v,(int,float)) and not isinstance(v,bool) else v for k,v in row.items()} for row in rows]
        actual=[{key:row[key] for key in FIELDS[name]} for row in evidence['tables'][name]]
        if normalized(numeric(tables[name]))!=normalized(numeric(actual)):
            raise ValueError(f'Desktop snapshot differs: {name}')
    metrics=evidence['metrics']
    overview=verify_overview(tables,evidence)
    if len(metrics)!=len(tables['DimScan']): raise ValueError('Missing quarterly DAX results')
    import math
    summaries={json.loads(row['scope'])[1]:row for row in tables['Summary'] if row['scope']!='all'}
    if len({row['scan_id'] for row in metrics})!=len(metrics): raise ValueError('Duplicate quarterly results')
    for row in metrics:
        summary=summaries[row['scan_id']]
        if row['observations']!=summary['observations'] or row['paired_count']!=0:
            raise ValueError('Quarterly count/production accuracy mismatch')
        if any(row[field] is not None for field in ('mae_cm','rmse_cm','bias_cm','mape_pct')):
            raise ValueError('Synthetic error cannot enter real accuracy')
        if row['demo_pairs']!=summary['paired_count'] or not math.isclose(row['demo_mae_cm'],summary['mae_cm'],abs_tol=1e-8):
            raise ValueError('Quarterly scenario metric mismatch')
    result=dict(engine=evidence['engine'],queried_at=evidence['queried_at'],
                observations=len(tables['FactObservation']),trees=len({r['tree_key'] for r in tables['FactObservation']}),
                scans=len(tables['DimScan']),growth_records=len(tables['FactGrowth']),desktop_data_verified=True,desktop_validated=False,
                scope='Table import and DAX verified; not field precision or full report-page acceptance.')
    result['overview']=overview
    (folder/'desktop-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('prepare');p.add_argument('--out',required=True)
    p=sub.add_parser('verify');p.add_argument('--folder',required=True);p.add_argument('--results',required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.out) if args.action=='prepare' else verify(args.folder,args.results),indent=2))
