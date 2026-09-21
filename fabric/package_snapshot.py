"""Build a local OneLake Files layout ZIP; does not upload anything."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

def package(source, output):
    source=Path(source); output=Path(output)
    raw=(source/'analytics.json').read_bytes()
    data=json.loads(raw); manifest=json.loads((source/'manifest.json').read_text())
    batch=hashlib.sha256(raw).hexdigest()[:16]
    entries={f'Files/arbor3d/silver/{batch}/analytics.json':raw}
    for name,digest in manifest['files'].items():
        if Path(name).name!=name: raise ValueError('Invalid manifest filename')
        contents=(source/name).read_bytes()
        if hashlib.sha256(contents).hexdigest()!=digest: raise ValueError(f'Snapshot hash mismatch: {name}')
        entries[f'Files/arbor3d/gold/{batch}/{name}']=contents
    entries[f'Files/arbor3d/gold/{batch}/manifest.json']=(source/'manifest.json').read_bytes()
    entries[f'Files/arbor3d/gold/{batch}/table-schema.json']=Path(__file__).with_name('table-schema.json').read_bytes()
    for row in data['tables']['DimScan']:
        raw_report=Path(row['source_file']).read_bytes()
        if hashlib.sha256(raw_report).hexdigest()!=row['source_sha256']: raise ValueError('Source report changed after analysis')
        # Hash path components to prevent path traversal from arbitrary site/scan IDs.
        site=hashlib.sha256(row['site_id'].encode()).hexdigest()[:16]
        scan=hashlib.sha256(row['scan_id'].encode()).hexdigest()[:16]
        entries[f'Files/arbor3d/bronze/{site}/{scan}/source.json']=raw_report
    output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(output,'w',ZIP_DEFLATED) as z:
        for name,contents in sorted(entries.items()): z.writestr(name,contents)
    return {'batch':batch,'files':len(entries),'output':str(output),'uploaded':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    print(json.dumps(package(a.input,a.output),indent=2))
