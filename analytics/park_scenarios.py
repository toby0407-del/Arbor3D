"""Export the App's stored park scenarios into a separate simulated analytics bundle."""
import argparse
import json
from pathlib import Path

from .core import build, export


def generate(output):
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'app/scenarios/parks/manifest.json').read_text(encoding='utf-8'))
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Choose an empty output folder; do not overwrite existing field data')
    reports, manuals, identities = [], [], []
    for site in manifest['sites']:
        inventory = json.loads((root / f"app/src/data/inventories/{site['scanId']}.json").read_text(encoding='utf-8'))
        for quarter in range(16):
            rows = [t['quarterly_observations'][quarter] for t in inventory['trees']]
            scan = rows[0]['scan_id']
            report = dict(scan_id=scan, created_at=rows[0]['date'], dataset_kind='simulated',
                          gps_available=False, num_trees=len(rows), trees=[])
            for row in rows:
                natural = dict(site_id=row['site_id'], scan_id=scan, local_tree_id=row['local_tree_id'])
                report['trees'].append(dict(Tree_ID=row['local_tree_id'], DBH_cm=row['simulated_ai_dbh_cm'],
                    Height_m=row['simulated_height_m'], DBH_method='simulated_circle',
                    DBH_note='simulated_' + row['scenario'], dbh_is_strict_breast_height=True))
                manuals.append(dict(natural, manual_dbh_cm=row['simulated_manual_dbh_cm'],
                    manual_height_m=row['simulated_height_m'], measured_at=row['date'], strict_13m=True))
                identities.append(dict(natural, persistent_tree_id=row['persistent_tree_id'], confirmed=True))
            source = output / 'reports' / f'{scan}.json'
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            reports.append((site['siteId'], str(source.resolve()), report))
    tables = build(reports, manuals, identities, allow_simulated=True)
    export(tables, output / 'analytics')
    (output / 'simulation.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return {name: len(rows) for name, rows in tables.items()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    print(json.dumps(generate(parser.parse_args().out), indent=2))
