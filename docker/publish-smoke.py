"""Verify real publication paths as the container's non-root application user."""
import json
from pathlib import Path
import sys

sys.path.insert(0, '/opt/arbor3d')
from scripts.postprocess_from_inbox import publish_report

repo = Path('/opt/arbor3d')
output = Path('/data/docker-publish-smoke')
output.mkdir(exist_ok=True)
photo = output / 'photo.jpg'
photo.write_bytes(b'publication-path-smoke-fixture')
report_path = output / 'park_inventory_report.json'
report_path.write_text(json.dumps({'scan_id':'sim-docker-publish', 'num_trees':1,
    'trees':[{'Tree_ID':'Tree_001', 'DBH_cm':20, 'Best_Photo':str(photo)}]}), encoding='utf-8')
published = publish_report(report_path, output, repo, Path('/data'),
                           'sim-docker-publish', 'docker-publish-test-path')
public = repo / 'app/public/scans/sim-docker-publish'
assert (public / 'inventory.json').is_file()
assert (public / published['trees'][0]['Best_Photo']).read_bytes() == photo.read_bytes()
assert (repo / 'app/src/data/inventories/sim-docker-publish.json').is_file()
bindings = json.loads((repo / 'app/public/scans/_bindings.json').read_text(encoding='utf-8'))
assert bindings['docker-publish-test-path'] == 'sim-docker-publish'
print('PASS: non-root report publication, media copy, source index and persistent path binding')
