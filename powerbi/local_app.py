"""Prepare local Desktop projects; publish only checked Desktop query results to the App."""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from analytics.core import build, export, FIELDS
from powerbi.build_project import generate


def verify_overview(tables, evidence):
    if 'overview' not in evidence: return None  # Older table-only verification files.
    if len(evidence['overview'])!=1: raise ValueError('Expected one unfiltered overview result')
    actual=evidence['overview'][0]
    latest={}
    for row in tables['FactObservation']:
        if row['tree_key'] not in latest or row['observed_at']>latest[row['tree_key']]['observed_at']:
            latest[row['tree_key']]=row
    keys={row['observation_key'] for row in latest.values()}
    carbon=[row['co2_equivalent_ton'] for row in tables['FactEstimate'] if row['observation_key'] in keys and row['co2_equivalent_ton'] is not None]
    kind=tables['Summary'][0]['dataset_kind']
    review=sum(row['review_required'] for row in latest.values())
    expected=dict(trees=len(latest),observations=len(tables['FactObservation']),latest_review_trees=review,
                  latest_review_rate=review/len(latest) if latest else None,latest_co2_ton=sum(carbon) if carbon else None,
                  growth_records=len(tables['FactGrowth']),formal_pairs=tables['Summary'][0]['paired_count'] if kind=='observed' else 0,
                  formal_mae=tables['Summary'][0]['mae_cm'] if kind=='observed' else None)
    for name,value in expected.items():
        result=actual[name]
        if value is None and result is not None or value is not None and (result is None or not math.isclose(value,result,rel_tol=1e-8,abs_tol=1e-8)):
            raise ValueError(f'Overview DAX mismatch: {name}')
    return actual


def prepare(inputs, output):
    inputs, output = Path(inputs), Path(output)
    index = json.loads((inputs / 'index.json').read_text(encoding='utf-8'))
    if output.exists() and any(output.iterdir()):
        raise ValueError('Choose a new output directory; Desktop edits are preserved')
    for kind in ('observed', 'simulated'):
        reports, manuals, sources = [], [], []
        for entry in index['entries']:
            if entry['dataset_kind'] != kind:
                continue
            source = inputs / (entry['scan_id'] + '.json')
            bundle = json.loads(source.read_text(encoding='utf-8'))
            site = 'fengchia' if kind == 'observed' else entry['scan_id']
            reports.append((site, str(source.resolve()), bundle['report']))
            manuals.extend(dict(r, site_id=site) for r in bundle['manual_measurements'])
            sources.append(entry)
        tables = build(reports, manuals, allow_simulated=kind == 'simulated')
        folder = output / kind
        export(tables, folder / 'analytics')
        generate(folder / 'analytics', folder / 'powerbi', clean_titles=True)
        (folder / 'sources.json').write_text(json.dumps(sources, indent=2), encoding='utf-8')
    return str(output.resolve())


def publish(folder, results, app_public):
    folder = Path(folder)
    canonical = json.loads((folder / 'analytics/analytics.json').read_text(encoding='utf-8'))['tables']
    evidence = json.loads(Path(results).read_text(encoding='utf-8-sig'))
    if evidence.get('engine') != 'Power BI Desktop / Analysis Services':
        raise ValueError('Desktop engine evidence required')
    # Matching all imported table rows protects against an old or unrelated open model.
    for name in ('DimScan', 'FactObservation', 'FactEstimate', 'FactGrowth'):
        actual = [{key:row[key] for key in FIELDS[name]} for row in evidence['tables'][name]]
        expected = canonical[name]
        row_key = {'DimScan': 'scan_key', 'FactObservation': 'observation_key',
                   'FactEstimate': 'observation_key', 'FactGrowth': 'to_observation_key'}[name]
        def normalized(rows):
            # CSV -> Tabular doubles may differ in their last binary digit.
            return sorted(({k: None if v == "" else round(v, 9) if isinstance(v, float) else v for k, v in r.items()} for r in rows),
                          key=lambda r: (r[row_key], str(r.get('source', ''))))
        # Dates are exported by the bridge as yyyy-MM-dd and missing values as null.
        if normalized(actual) != normalized(expected):
            raise ValueError(f'Desktop data differs from current snapshot: {name}; refresh Desktop')
    sources = json.loads((folder / 'sources.json').read_text(encoding='utf-8'))
    verify_overview(canonical,evidence)
    metrics = evidence['metrics']
    if len(metrics) != len(sources):
        raise ValueError('Desktop metrics must cover each current scan exactly once')
    output = Path(app_public) / 'analysis'
    output.mkdir(parents=True, exist_ok=True)
    published, payloads = [], []
    for source in sources:
        scan = source['scan_id']
        rows = [r for r in metrics if r['scan_id'] == scan]
        if len(rows) != 1:
            raise ValueError(f'Missing or duplicate Desktop metric: {scan}')
        metric = rows[0]
        summary = next(r for r in canonical['Summary'] if r['scope'] != 'all' and json.loads(r['scope'])[1] == scan)
        for field in ('observations', 'paired_count', 'mae_cm', 'rmse_cm', 'bias_cm', 'mape_pct', 'review_count'):
            # Synthetic error belongs to demo metrics; formal accuracy stays blank.
            value = summary[field]
            if source['dataset_kind'] == 'simulated' and field in ('paired_count', 'mae_cm', 'rmse_cm', 'bias_cm', 'mape_pct'):
                value = 0 if field == 'paired_count' else None
            actual = metric[field]
            if value is None and actual is not None or value is not None and (actual is None or not math.isclose(value, actual, rel_tol=1e-8, abs_tol=1e-8)):
                raise ValueError(f'DAX reconciliation failed: {scan}/{field}')
        observations = [r for r in canonical['FactObservation'] if json.loads(r['scan_key'])[1] == scan]
        estimates = [r for r in canonical['FactEstimate'] if json.loads(r['scan_key'])[1] == scan]
        dbhs = [r['auto_dbh_cm'] for r in observations if r['auto_dbh_cm'] is not None]
        carbon = [r['co2_equivalent_ton'] for r in estimates if r['co2_equivalent_ton'] is not None]
        checks = dict(average_dbh_cm=sum(dbhs)/len(dbhs) if dbhs else None,
                      co2_ton=sum(carbon) if carbon else None,
                      demo_pairs=summary['paired_count'] or None if source['dataset_kind']=='simulated' else None,
                      demo_mae_cm=summary['mae_cm'] if source['dataset_kind']=='simulated' else None)
        for field, value in checks.items():
            actual = metric[field]
            if value is None and actual is not None or value is not None and (actual is None or not math.isclose(value, actual, rel_tol=1e-8, abs_tol=1e-8)):
                raise ValueError(f'DAX reconciliation failed: {scan}/{field}')
        payload = dict(schema_version=1, scan_id=scan, dataset_kind=source['dataset_kind'],
                       input_fingerprint=source['fingerprint'], engine=evidence['engine'],
                       calculated_at=evidence['queried_at'], published_at=datetime.now(timezone.utc).isoformat(),
                       metrics=metric,
                       evidence_sha256=hashlib.sha256(Path(results).read_bytes()).hexdigest())
        payloads.append((scan, payload))
    # Check every scan before replacing any existing App snapshot.
    for scan, payload in payloads:
        target = output / f'{scan}.json'
        temp = target.with_suffix('.tmp')
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        temp.replace(target)
        published.append(scan)
    return published


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    a = sub.add_parser('prepare'); a.add_argument('--inputs', required=True); a.add_argument('--out', required=True)
    a = sub.add_parser('publish'); a.add_argument('--folder', required=True); a.add_argument('--results', required=True); a.add_argument('--app-public', required=True)
    args = p.parse_args()
    result = prepare(args.inputs, args.out) if args.action == 'prepare' else publish(args.folder, args.results, args.app_public)
    print(json.dumps(result))
